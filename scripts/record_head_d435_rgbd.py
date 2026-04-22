#!/usr/bin/env /usr/bin/python3

import argparse
import json
import os
import queue
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
    from cv_bridge import CvBridge
    from sensor_msgs.msg import CameraInfo, Image
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import cv2
    import message_filters
    import rospy
    from cv_bridge import CvBridge
    from sensor_msgs.msg import CameraInfo, Image


@dataclass
class FramePacket:
    seq: int
    stamp: float
    color_msg: Image
    depth_msg: Image


class HeadD435RgbdRecorder:
    def __init__(self, args):
        self.args = args
        self.bridge = CvBridge()
        self.frame_queue: "queue.Queue[Optional[FramePacket]]" = queue.Queue(maxsize=args.queue_size)
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.shutdown_event = threading.Event()
        self.state_lock = threading.Lock()
        self.info_lock = threading.Lock()

        self.recording = False
        self.current_episode_dir: Optional[Path] = None
        self.current_color_dir: Optional[Path] = None
        self.current_depth_dir: Optional[Path] = None
        self.current_episode_metadata = {}
        self.frame_seq = 0
        self.saved_frames = 0

        self.latest_color_info: Optional[CameraInfo] = None
        self.latest_depth_info: Optional[CameraInfo] = None

        self.dataset_dir = Path(args.dataset_root).expanduser() / args.task_name
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dataset_dir / "head_d435_rgbd_recorder.log"

    def log(self, event: str, **kwargs):
        payload = {
            "wall_time": time.time(),
            "event": event,
            **kwargs,
        }
        line = json.dumps(payload, ensure_ascii=True)
        print(line, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _find_next_episode_index(self) -> int:
        max_index = -1
        for entry in self.dataset_dir.iterdir():
            if not entry.is_dir():
                continue
            if not entry.name.startswith("episode"):
                continue
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
            "binning_x": msg.binning_x,
            "binning_y": msg.binning_y,
        }

    def _save_json(self, path: Path, payload: dict):
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)

    def _try_get_depth_scale(self) -> float:
        if self.args.depth_scale is not None:
            return self.args.depth_scale

        param_candidates = [
            f"/{self.args.camera_ns}/depth_module/depth_units",
            f"/{self.args.camera_ns}/realsense2_camera/depth_module/depth_units",
            "/camera/depth_module/depth_units",
        ]
        for name in param_candidates:
            value = rospy.get_param(name, None)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass

        return 0.001

    def _write_episode_metadata(self):
        if self.current_episode_dir is None:
            return

        payload = {
            "task_name": self.args.task_name,
            "camera_name": self.args.camera_name,
            "camera_ns": self.args.camera_ns,
            "rgb_topic": self.args.rgb_topic,
            "depth_topic": self.args.depth_topic,
            "rgb_info_topic": self.args.rgb_info_topic,
            "depth_info_topic": self.args.depth_info_topic,
            "depth_encoding": self.current_episode_metadata.get("depth_encoding"),
            "depth_scale_m_per_unit": self.current_episode_metadata.get("depth_scale_m_per_unit"),
            "depth_unit_note": self.current_episode_metadata.get("depth_unit_note"),
            "started_at_wall_time": self.current_episode_metadata.get("started_at_wall_time"),
            "ended_at_wall_time": time.time() if self.recording is False else None,
            "saved_frames": self.saved_frames,
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
            self.current_episode_metadata = {
                "depth_scale_m_per_unit": self._try_get_depth_scale(),
                "depth_unit_note": "raw 16UC1 is typically millimeters; depth_in_meters.npy is meters",
                "started_at_wall_time": time.time(),
            }
            self.frame_seq = 0
            self.saved_frames = 0
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

            self.log("episode_started", episode=str(episode_dir), depth_scale_m_per_unit=self.current_episode_metadata["depth_scale_m_per_unit"])

    def _stop_episode(self):
        with self.state_lock:
            if not self.recording:
                self.log("stop_ignored", reason="not_recording")
                return
            episode_dir = self.current_episode_dir
            self.recording = False
            self._write_episode_metadata()
            self.log("episode_stopped", episode=str(episode_dir), saved_frames=self.saved_frames)
            self.current_episode_dir = None
            self.current_color_dir = None
            self.current_depth_dir = None
            self.current_episode_metadata = {}

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

        stamp = color_msg.header.stamp.to_sec()
        packet = FramePacket(seq=seq, stamp=stamp, color_msg=color_msg, depth_msg=depth_msg)
        try:
            self.frame_queue.put_nowait(packet)
        except queue.Full:
            self.log("frame_dropped", reason="writer_queue_full", seq=seq, stamp=stamp)

    def _convert_depth(self, depth_msg: Image):
        depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding="passthrough")
        encoding = depth_msg.encoding.lower()
        scale = self.current_episode_metadata["depth_scale_m_per_unit"]

        if depth.dtype == np.uint16 or encoding == "16uc1":
            depth_raw = depth
            depth_meters = depth.astype("float32") * float(scale)
            note = "raw png stores uint16 depth units from ROS topic; with RealSense this is usually millimeters"
        elif depth.dtype == np.float32 or encoding == "32fc1":
            depth_meters = depth.astype("float32")
            depth_raw = None
            note = "raw topic is already float32 meters"
        else:
            raise RuntimeError(f"Unsupported depth dtype={depth.dtype} encoding={depth_msg.encoding}")

        self.current_episode_metadata["depth_encoding"] = depth_msg.encoding
        self.current_episode_metadata["depth_unit_note"] = note
        return depth_raw, depth_meters

    def _writer_loop(self):
        while not self.shutdown_event.is_set():
            try:
                packet = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if packet is None:
                return

            with self.state_lock:
                if self.current_episode_dir is None or self.current_color_dir is None or self.current_depth_dir is None:
                    continue
                color_dir = self.current_color_dir
                depth_dir = self.current_depth_dir

            stem = f"{packet.seq:06d}_{packet.stamp:.6f}"

            try:
                color = self.bridge.imgmsg_to_cv2(packet.color_msg, desired_encoding="bgr8")
                depth_raw, depth_meters = self._convert_depth(packet.depth_msg)

                color_path = color_dir / f"{stem}.png"
                depth_raw_path = depth_dir / f"{stem}.png"
                depth_m_path = depth_dir / f"{stem}_meters.npy"

                if not cv2.imwrite(str(color_path), color):
                    raise RuntimeError(f"Failed to write color image: {color_path}")

                if depth_raw is not None:
                    if not cv2.imwrite(str(depth_raw_path), depth_raw):
                        raise RuntimeError(f"Failed to write depth image: {depth_raw_path}")
                else:
                    fallback_raw = (depth_meters * 1000.0).astype("uint16")
                    if not cv2.imwrite(str(depth_raw_path), fallback_raw):
                        raise RuntimeError(f"Failed to write fallback depth image: {depth_raw_path}")

                np.save(str(depth_m_path), depth_meters)

                with self.state_lock:
                    self.saved_frames += 1
            except Exception as exc:
                self.log("write_failed", error=str(exc), seq=packet.seq, stamp=packet.stamp)

    def run(self):
        rospy.init_node("head_d435_rgbd_recorder", anonymous=True)

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
        self.log(
            "recorder_ready",
            dataset_dir=str(self.dataset_dir),
            rgb_topic=self.args.rgb_topic,
            depth_topic=self.args.depth_topic,
            depth_scale_m_per_unit=self._try_get_depth_scale(),
        )

        print("Commands: s=start episode, e=end episode, q=quit", flush=True)
        while not rospy.is_shutdown():
            try:
                command = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                command = "q"

            if command == "s":
                self._start_episode()
            elif command == "e":
                self._stop_episode()
            elif command == "q":
                self._stop_episode()
                break
            elif command == "":
                continue
            else:
                print("Unknown command. Use: s / e / q", flush=True)

        self.shutdown_event.set()
        try:
            self.frame_queue.put_nowait(None)
        except queue.Full:
            pass
        self.writer_thread.join(timeout=2.0)
        self.log("recorder_exited")


def parse_args():
    parser = argparse.ArgumentParser(description="Standalone recorder for head D435 RGB + depth episodes.")
    parser.add_argument("--task-name", default="head_d435_rgbd")
    parser.add_argument("--dataset-root", default=os.path.expanduser("~/agilex"))
    parser.add_argument("--camera-name", default="headD435")
    parser.add_argument("--camera-ns", default="camera")
    parser.add_argument("--rgb-topic", default="/camera/color/image_raw")
    parser.add_argument("--depth-topic", default="/camera/aligned_depth_to_color/image_raw")
    parser.add_argument("--rgb-info-topic", default="/camera/color/camera_info")
    parser.add_argument("--depth-info-topic", default="/camera/aligned_depth_to_color/camera_info")
    parser.add_argument("--depth-scale", type=float, default=None, help="Meters per raw depth unit. Default tries ROS param, else 0.001.")
    parser.add_argument("--sync-queue-size", type=int, default=30)
    parser.add_argument("--sync-slop-sec", type=float, default=0.03)
    parser.add_argument("--queue-size", type=int, default=256)
    return parser.parse_args()


def main():
    args = parse_args()
    recorder = HeadD435RgbdRecorder(args)
    recorder.run()


if __name__ == "__main__":
    raise SystemExit(main())
