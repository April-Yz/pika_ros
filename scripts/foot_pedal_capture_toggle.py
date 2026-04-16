#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import os
import select
import signal
import struct
import sys
import time
from pathlib import Path

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
    import rospy
    from data_msgs.srv import CaptureService, CaptureServiceRequest
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import rospy
    from data_msgs.srv import CaptureService, CaptureServiceRequest


EV_KEY = 0x01
KEY_C = 46
KEY_PRESS = 1
EVENT_STRUCT = struct.Struct("llHHI")


class FootPedalCaptureToggle:
    def __init__(self, args):
        self.args = args
        self.recording = False
        self.next_episode = self._find_next_episode(args.dataset_dir)
        self.capture_srv = None
        self.fd = None
        self.device = None
        self.log_path = Path(args.dataset_dir).expanduser() / "foot_pedal_capture.log"

    @staticmethod
    def _banner(title, detail=""):
        line = "=" * 72
        print(line, flush=True)
        print(title, flush=True)
        if detail:
            print(detail, flush=True)
        print(line, flush=True)

    def _append_log(self, event, detail=""):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        iso = dt.datetime.fromtimestamp(now).isoformat()
        line = f"{iso}\t{now:.6f}\t{event}"
        if detail:
            line += f"\t{detail}"
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")

    @staticmethod
    def _find_next_episode(dataset_dir):
        dataset_path = Path(dataset_dir).expanduser()
        max_idx = -1
        if dataset_path.is_dir():
            for entry in dataset_path.iterdir():
                if not entry.is_dir() or not entry.name.startswith("episode"):
                    continue
                suffix = entry.name[len("episode") :]
                if suffix.isdigit():
                    max_idx = max(max_idx, int(suffix))
        return max_idx + 1

    def _call_capture(self, start, end, episode_index):
        req = CaptureServiceRequest()
        req.start = start
        req.end = end
        req.episode_index = episode_index
        req.dataset_dir = self.args.dataset_dir
        req.instructions = self.args.instructions
        return self.capture_srv(req)

    def start_recording(self):
        episode = self.next_episode
        rospy.loginfo("Right pedal pressed. Requesting capture start for episode%d.", episode)
        self._banner("PEDAL: START REQUEST", f"episode{episode}")
        self._append_log("pedal_start_request", f"episode{episode}")
        try:
            res = self._call_capture(True, False, episode)
        except Exception as exc:
            rospy.logwarn("Capture start failed: %s", exc)
            self._banner("PEDAL: START FAILED", str(exc))
            self._append_log("pedal_start_failed", str(exc))
            return
        if not res.success:
            rospy.logwarn("Capture start rejected: %s", res.message)
            self._banner("PEDAL: START REJECTED", res.message)
            self._append_log("pedal_start_rejected", res.message)
            return
        self.recording = True
        self.next_episode += 1
        rospy.loginfo("Capture started successfully: episode%d", episode)
        self._banner("CAPTURE STARTED", f"episode{episode}")
        self._append_log("capture_started", f"episode{episode}")

    def stop_recording(self):
        rospy.loginfo("Right pedal pressed. Requesting capture stop.")
        self._banner("PEDAL: STOP REQUEST")
        self._append_log("pedal_stop_request")
        try:
            res = self._call_capture(False, True, -1)
        except Exception as exc:
            rospy.logwarn("Capture stop failed: %s", exc)
            self.recording = False
            self._banner("PEDAL: STOP FAILED", str(exc))
            self._append_log("pedal_stop_failed", str(exc))
            return
        if not res.success:
            rospy.logwarn("Capture stop rejected: %s", res.message)
            self.recording = False
            self._banner("PEDAL: STOP REJECTED", res.message)
            self._append_log("pedal_stop_rejected", res.message)
            return
        self.recording = False
        rospy.loginfo("Capture stopped successfully.")
        self._banner("CAPTURE STOPPED")
        self._append_log("capture_stopped")

    def toggle(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def open_device(self):
        device_path = Path(self.args.device).expanduser()
        self.device = str(device_path)
        self.fd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
        rospy.loginfo("Listening to foot pedal device: %s", self.device)

    def close_device(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def process_event(self, event_bytes):
        if len(event_bytes) != EVENT_STRUCT.size:
            return
        _, _, ev_type, code, value = EVENT_STRUCT.unpack(event_bytes)
        if ev_type == EV_KEY and code == KEY_C and value == KEY_PRESS:
            self._append_log("pedal_key_down", "KEY_C")
            self.toggle()

    def run(self):
        rospy.init_node("foot_pedal_capture_toggle", anonymous=True)
        rospy.wait_for_service("/data_tools_dataCapture/capture_service")
        self.capture_srv = rospy.ServiceProxy("/data_tools_dataCapture/capture_service", CaptureService)
        self.open_device()
        rospy.loginfo(
            "Foot pedal capture toggle ready. Right pedal(KEY_C) toggles start/stop. dataset_dir=%s next_episode=episode%d",
            self.args.dataset_dir,
            self.next_episode,
        )
        self._banner(
            "FOOT PEDAL CAPTURE READY",
            f"device={self.device}\nright pedal KEY_C toggles capture\nnext episode=episode{self.next_episode}",
        )
        self._append_log("foot_pedal_ready", f"device={self.device} next_episode=episode{self.next_episode}")

        while not rospy.is_shutdown():
            readable, _, _ = select.select([self.fd], [], [], 0.2)
            if self.fd not in readable:
                continue
            try:
                data = os.read(self.fd, EVENT_STRUCT.size * 32)
            except BlockingIOError:
                continue
            for offset in range(0, len(data), EVENT_STRUCT.size):
                self.process_event(data[offset:offset + EVENT_STRUCT.size])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Use the right foot pedal (KEY_C) to toggle ROS data capture start/stop."
    )
    parser.add_argument(
        "--device",
        default="/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd",
        help="Foot pedal keyboard device path.",
    )
    parser.add_argument("--dataset-dir", default=os.path.expanduser("~/agilex/data"))
    parser.add_argument("--instructions", default="[null]")
    return parser.parse_args()


def main():
    args = parse_args()
    toggle = FootPedalCaptureToggle(args)

    def _shutdown(*_args):
        try:
            toggle.close_device()
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    try:
        toggle.run()
    finally:
        toggle.close_device()


if __name__ == "__main__":
    sys.exit(main())
