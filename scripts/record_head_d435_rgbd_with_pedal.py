#!/usr/bin/env /usr/bin/python3

import argparse
import json
import os
import queue
import select
import struct
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


def _bootstrap_ros_python():
    script_dir = Path(__file__).resolve().parent
    workspace_dir = script_dir.parent
    candidates = [
        "/opt/ros/noetic/lib/python3/dist-packages",
        str(workspace_dir / "install" / "lib" / "python3" / "dist-packages"),
        str(workspace_dir / "devel" / "lib" / "python3" / "dist-packages"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.append(candidate)


try:
    import cv2
    import message_filters
    import rospy
    from sensor_msgs.msg import CameraInfo, Image
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import cv2
    import message_filters
    import rospy
    from sensor_msgs.msg import CameraInfo, Image


EV_KEY = 0x01
KEY_C = 46
KEY_PRESS = 1
EVENT_STRUCT = struct.Struct("llHHI")


@dataclass
class FramePacket:
    seq: int
    stamp: float
    color_msg: Image
    depth_msg: Image


class HeadD435PedalRecorder:
    def __init__(self, args):
        self.args = args
        self.dataset_dir = Path(args.dataset_root).expanduser() / args.task_name
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dataset_dir / "head_d435_pedal_recorder.log"

        self.recording = False
        self.frame_seq = 0
        self.saved_frames = 0
        self.current_episode_dir: Optional[Path] = None
        self.current_color_dir: Optional[Path] = None
        self.current_depth_dir: Optional[Path] = None
        self.current_episode_meta = {}
        self.latest_color_info: Optional[CameraInfo] = None
        self.latest_depth_info: Optional[CameraInfo] = None
        self.last_synced_stamp: Optional[float] = None

        self.frame_queue: "queue.Queue[Optional[FramePacket]]" = queue.Queue(maxsize=args.queue_size)
        self.state_lock = threading.Lock()
        self.info_lock = threading.Lock()
        self.stop_event = threading.Event()

        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.pedal_thread = threading.Thread(target=self._pedal_loop, daemon=True)

    def log(self, event: str, **kwargs):
        payload = {"wall_time": time.time(), "event": event, **kwargs}
        line = json.dumps(payload, ensure_ascii=True)
        print(line, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _find_next_episode_index(self) -> int:
        max_index = -1
        for entry in self.dataset_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("episode"):
                suffix = entry.name[len("episode") :]
                if suffix.isdigit():
                    max_index = max(max_index, int(suffix))
        return max_index + 1

    def _camera_info_to_dict(self, msg: CameraInfo) -> dict:
        return {
            "header": {
                "seq": msg.header.seq,
                "stamp": msg.header.stamp.to_sec(),
                "frame_id": msg.header.frame_id,
            },
            "height": msg.height,
            "width": msg.width,
            "distortion_model": msg.distortion_model,
            "D": list(msg.D),
            "K": list(msg.K),
            "R": list(msg.R),
            "P": list(msg.P),
        }

    def _save_json(self, path: Path, payload: dict):
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)

    def _depth_scale_m_per_unit(self) -> float:
        if self.args.depth_scale is not None:
            return self.args.depth_scale
        param_candidates = [
            f"/{self.args.camera_ns}/depth_module/depth_units",
            f"/{self.args.camera_ns}/realsense2_camera/depth_module/depth_units",
            "/camera/depth_module/depth_units",
        ]
        for param_name in param_candidates:
            value = rospy.get_param(param_name, None)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.001

    def _write_episode_meta(self):
        if self.current_episode_dir is None:
            return
        payload = {
            "task_name": self.args.task_name,
            "camera_name": self.args.camera_name,
            "rgb_topic": self.args.rgb_topic,
            "depth_topic": self.args.depth_topic,
            "rgb_info_topic": self.args.rgb_info_topic,
            "depth_info_topic": self.args.depth_info_topic,
            "depth_encoding": self.current_episode_meta.get("depth_encoding"),
            "depth_scale_m_per_unit": self.current_episode_meta.get("depth_scale_m_per_unit"),
            "depth_unit_note": self.current_episode_meta.get("depth_unit_note"),
            "saved_frames": self.saved_frames,
            "started_at_wall_time": self.current_episode_meta.get("started_at_wall_time"),
            "ended_at_wall_time": time.time(),
        }
        self._save_json(self.current_episode_dir / "head_d435_rgbd_meta.json", payload)

    def _start_episode(self):
        with self.state_lock:
            if self.recording:
                self.log("start_ignored", reason="already_recording")
                return

            episode_index = self._find_next_episode_index()
            episode_dir = self.dataset_dir / f"episode{episode_index}"
            color_dir = episode_dir / "camera" / "color" / self.args.camera_name
            depth_dir = episode_dir / "camera" / "depth" / self.args.camera_name
            color_dir.mkdir(parents=True, exist_ok=False)
            depth_dir.mkdir(parents=True, exist_ok=False)

            self.current_episode_dir = episode_dir
            self.current_color_dir = color_dir
            self.current_depth_dir = depth_dir
            self.current_episode_meta = {
                "started_at_wall_time": time.time(),
                "depth_scale_m_per_unit": self._depth_scale_m_per_unit(),
                "depth_unit_note": "raw depth png is usually uint16 millimeters; *_meters.npy is meters",
            }
            self.saved_frames = 0
            self.frame_seq = 0
            self.recording = True

            with self.info_lock:
                if self.latest_color_info is not None:
                    self._save_json(
                        episode_dir / "camera" / "color" / f"{self.args.camera_name}_camera_info.json",
                        self._camera_info_to_dict(self.latest_color_info),
                    )
                if self.latest_depth_info is not None:
                    self._save_json(
                        episode_dir / "camera" / "depth" / f"{self.args.camera_name}_camera_info.json",
                        self._camera_info_to_dict(self.latest_depth_info),
                    )

            self.log(
                "episode_started",
                episode=str(episode_dir),
                depth_scale_m_per_unit=self.current_episode_meta["depth_scale_m_per_unit"],
            )

    def _stop_episode(self):
        with self.state_lock:
            if not self.recording:
                self.log("stop_ignored", reason="not_recording")
                return
            episode_dir = self.current_episode_dir
            self.recording = False
            self._write_episode_meta()
            self.current_episode_dir = None
            self.current_color_dir = None
            self.current_depth_dir = None
            self.current_episode_meta = {}
            self.log("episode_stopped", episode=str(episode_dir), saved_frames=self.saved_frames)
            if self.saved_frames == 0:
                self.log(
                    "episode_empty",
                    episode=str(episode_dir),
                    reason="no synchronized rgb+depth frames received during recording window",
                    rgb_topic=self.args.rgb_topic,
                    depth_topic=self.args.depth_topic,
                    last_synced_stamp=self.last_synced_stamp,
                )

    def _toggle_episode(self):
        if self.recording:
            self._stop_episode()
        else:
            self._start_episode()

    def _color_info_callback(self, msg: CameraInfo):
        with self.info_lock:
            self.latest_color_info = msg

    def _depth_info_callback(self, msg: CameraInfo):
        with self.info_lock:
            self.latest_depth_info = msg

    def _sync_callback(self, color_msg: Image, depth_msg: Image):
        with self.state_lock:
            if not self.recording:
                return
            seq = self.frame_seq
            self.frame_seq += 1
        packet = FramePacket(seq=seq, stamp=color_msg.header.stamp.to_sec(), color_msg=color_msg, depth_msg=depth_msg)
        self.last_synced_stamp = packet.stamp
        try:
            self.frame_queue.put_nowait(packet)
        except queue.Full:
            self.log("frame_dropped", reason="queue_full", seq=seq, stamp=packet.stamp)

    def _pedal_loop(self):
        device_path = Path(self.args.device).expanduser()
        if not device_path.exists():
            self.log("pedal_error", reason="device_not_found", device=str(device_path))
            return

        with device_path.open("rb", buffering=0) as device:
            self.log("pedal_ready", device=str(device_path))
            while not self.stop_event.is_set():
                readable, _, _ = select.select([device], [], [], 0.2)
                if not readable:
                    continue
                event = device.read(EVENT_STRUCT.size)
                if len(event) != EVENT_STRUCT.size:
                    continue
                _, _, event_type, code, value = EVENT_STRUCT.unpack(event)
                if event_type != EV_KEY or code != KEY_C or value != KEY_PRESS:
                    continue
                self.log("pedal_toggle_pressed")
                self._toggle_episode()

    def _convert_depth(self, depth_msg: Image):
        depth = self._image_msg_to_numpy(depth_msg)
        encoding = depth_msg.encoding.lower()
        scale = self.current_episode_meta["depth_scale_m_per_unit"]

        if depth.dtype == np.uint16 or encoding == "16uc1":
            depth_raw = depth
            depth_m = depth.astype(np.float32) * float(scale)
            note = "source depth is uint16; for RealSense this is generally millimeters"
        elif depth.dtype == np.float32 or encoding == "32fc1":
            depth_m = depth.astype(np.float32)
            depth_raw = np.clip(depth_m * 1000.0, 0, 65535).astype(np.uint16)
            note = "source depth is float32 meters; png fallback is depth*1000 as uint16"
        else:
            raise RuntimeError(f"Unsupported depth encoding={depth_msg.encoding} dtype={depth.dtype}")

        self.current_episode_meta["depth_encoding"] = depth_msg.encoding
        self.current_episode_meta["depth_unit_note"] = note
        return depth_raw, depth_m

    @staticmethod
    def _reshape_image_buffer(msg: Image, dtype) -> np.ndarray:
        itemsize = np.dtype(dtype).itemsize
        channels = int(msg.step / (itemsize * msg.width))
        row = np.frombuffer(msg.data, dtype=dtype)
        if channels == 1:
            return row.reshape(msg.height, msg.step // itemsize)[:, : msg.width].copy()
        reshaped = row.reshape(msg.height, msg.step // itemsize)
        reshaped = reshaped[:, : msg.width * channels]
        return reshaped.reshape(msg.height, msg.width, channels).copy()

    def _image_msg_to_numpy(self, msg: Image) -> np.ndarray:
        encoding = msg.encoding.lower()
        if encoding == "rgb8":
            image = self._reshape_image_buffer(msg, np.uint8)
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if encoding == "bgr8":
            return self._reshape_image_buffer(msg, np.uint8)
        if encoding == "mono8":
            return self._reshape_image_buffer(msg, np.uint8)
        if encoding == "16uc1":
            return self._reshape_image_buffer(msg, np.uint16)
        if encoding == "32fc1":
            return self._reshape_image_buffer(msg, np.float32)
        raise RuntimeError(f"Unsupported image encoding={msg.encoding}")

    def _writer_loop(self):
        while not self.stop_event.is_set():
            try:
                packet = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if packet is None:
                break

            with self.state_lock:
                color_dir = self.current_color_dir
                depth_dir = self.current_depth_dir
            if color_dir is None or depth_dir is None:
                continue

            stem = f"{packet.seq:06d}_{packet.stamp:.6f}"
            try:
                color = self._image_msg_to_numpy(packet.color_msg)
                depth_raw, depth_m = self._convert_depth(packet.depth_msg)

                color_path = color_dir / f"{stem}.png"
                depth_png_path = depth_dir / f"{stem}.png"
                depth_npy_path = depth_dir / f"{stem}_meters.npy"

                if not cv2.imwrite(str(color_path), color):
                    raise RuntimeError(f"Failed to write {color_path}")
                if not cv2.imwrite(str(depth_png_path), depth_raw):
                    raise RuntimeError(f"Failed to write {depth_png_path}")
                np.save(str(depth_npy_path), depth_m)

                with self.state_lock:
                    self.saved_frames += 1
            except Exception as exc:
                self.log("write_failed", seq=packet.seq, stamp=packet.stamp, error=str(exc))

    def _wait_for_topics(self):
        topic_map = dict(rospy.get_published_topics())
        missing = []
        for topic in [self.args.rgb_topic, self.args.depth_topic, self.args.rgb_info_topic, self.args.depth_info_topic]:
            if topic not in topic_map:
                missing.append(topic)
        if missing:
            self.log("topic_missing", missing_topics=missing)

    def run(self):
        rospy.init_node("head_d435_pedal_rgbd_recorder", anonymous=True)
        self._wait_for_topics()

        rospy.Subscriber(self.args.rgb_info_topic, CameraInfo, self._color_info_callback, queue_size=1)
        rospy.Subscriber(self.args.depth_info_topic, CameraInfo, self._depth_info_callback, queue_size=1)

        color_sub = message_filters.Subscriber(self.args.rgb_topic, Image)
        depth_sub = message_filters.Subscriber(self.args.depth_topic, Image)
        sync = message_filters.ApproximateTimeSynchronizer(
            [color_sub, depth_sub],
            queue_size=self.args.sync_queue_size,
            slop=self.args.sync_slop_sec,
        )
        sync.registerCallback(self._sync_callback)

        self.writer_thread.start()
        self.pedal_thread.start()
        self.log(
            "recorder_ready",
            dataset_dir=str(self.dataset_dir),
            pedal_device=self.args.device,
            rgb_topic=self.args.rgb_topic,
            depth_topic=self.args.depth_topic,
            note="right pedal KEY_C toggles start/stop; left and middle pedals are ignored",
        )

        try:
            rospy.spin()
        finally:
            self._stop_episode()
            self.stop_event.set()
            try:
                self.frame_queue.put_nowait(None)
            except queue.Full:
                pass
            self.writer_thread.join(timeout=2.0)
            self.pedal_thread.join(timeout=2.0)
            self.log("recorder_exited")


def parse_args():
    parser = argparse.ArgumentParser(description="Record head D435 RGB + depth, controlled only by right foot pedal.")
    parser.add_argument("--task-name", default="head_d435_rgbd")
    parser.add_argument("--dataset-root", default=os.path.expanduser("~/agilex/human"))
    parser.add_argument("--camera-name", default="headD435")
    parser.add_argument("--camera-ns", default="camera")
    parser.add_argument("--rgb-topic", default="/camera/color/image_raw")
    parser.add_argument("--depth-topic", default="/camera/aligned_depth_to_color/image_raw")
    parser.add_argument("--rgb-info-topic", default="/camera/color/camera_info")
    parser.add_argument("--depth-info-topic", default="/camera/aligned_depth_to_color/camera_info")
    parser.add_argument("--device", default="/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd")
    parser.add_argument("--depth-scale", type=float, default=None, help="meters per raw depth unit; default tries ROS param, else 0.001")
    parser.add_argument("--sync-queue-size", type=int, default=30)
    parser.add_argument("--sync-slop-sec", type=float, default=0.03)
    parser.add_argument("--queue-size", type=int, default=256)
    return parser.parse_args()


def main():
    args = parse_args()
    recorder = HeadD435PedalRecorder(args)
    recorder.run()


if __name__ == "__main__":
    raise SystemExit(main())
