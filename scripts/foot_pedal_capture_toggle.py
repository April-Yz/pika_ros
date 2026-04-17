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
from typing import List, Sequence, Tuple

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
    from data_msgs.msg import Gripper
    from data_msgs.srv import CaptureService, CaptureServiceRequest
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import JointState
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import rospy
    from data_msgs.msg import Gripper
    from data_msgs.srv import CaptureService, CaptureServiceRequest
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import JointState


EV_KEY = 0x01
KEY_A = 30
KEY_B = 48
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
        self.state_log_path = Path(args.dataset_dir).expanduser() / "foot_pedal_state_snapshot.log"
        self.state_md_path = Path(args.dataset_dir).expanduser() / "foot_pedal_state_snapshot.md"

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

    def _append_state_log(self, event: str, detail: str = ""):
        self.state_log_path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        iso = dt.datetime.fromtimestamp(now).isoformat()
        line = f"{iso}\t{now:.6f}\t{event}"
        if detail:
            line += f"\t{detail}"
        with self.state_log_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")

    @staticmethod
    def _format_joint_state(topic: str, msg: JointState) -> str:
        names = list(msg.name)
        positions = list(msg.position)
        pairs = []
        count = min(len(names), len(positions))
        for idx in range(count):
            pairs.append(f"{names[idx]}={positions[idx]:.6f}")
        if not pairs and positions:
            for idx, position in enumerate(positions):
                pairs.append(f"joint{idx + 1}={position:.6f}")
        return f"{topic}: " + (", ".join(pairs) if pairs else "no positions")

    @staticmethod
    def _format_pose(topic: str, msg: PoseStamped) -> str:
        pose = msg.pose
        return (
            f"{topic}: "
            f"pos=({pose.position.x:.6f}, {pose.position.y:.6f}, {pose.position.z:.6f}) "
            f"quat=({pose.orientation.x:.6f}, {pose.orientation.y:.6f}, "
            f"{pose.orientation.z:.6f}, {pose.orientation.w:.6f})"
        )

    @staticmethod
    def _format_gripper(topic: str, msg: Gripper) -> str:
        return (
            f"{topic}: "
            f"angle={msg.angle:.6f}, distance={msg.distance:.6f}, velocity={msg.velocity:.6f}, "
            f"effort={msg.effort:.6f}, enable={msg.enable}, error={msg.error}, status={msg.status}"
        )

    @staticmethod
    def _wait_for_message(topic: str, msg_type, timeout: float = 1.0):
        try:
            return rospy.wait_for_message(topic, msg_type, timeout=timeout)
        except rospy.ROSException:
            return None

    @staticmethod
    def _published_topic_map() -> dict:
        return dict(rospy.get_published_topics())

    def _collect_first_available(
        self,
        candidates: Sequence[Tuple[str, str, object]],
        allow_multiple: bool = True,
    ) -> List[Tuple[str, object]]:
        published = self._published_topic_map()
        collected: List[Tuple[str, object]] = []
        for topic, expected_type, msg_type in candidates:
            actual_type = published.get(topic)
            if actual_type != expected_type:
                continue
            msg = self._wait_for_message(topic, msg_type)
            if msg is None:
                continue
            collected.append((topic, msg))
            if not allow_multiple:
                break
        return collected

    def _build_snapshot_markdown(
        self,
        iso: str,
        joint_states: Sequence[Tuple[str, JointState]],
        poses: Sequence[Tuple[str, PoseStamped]],
        grippers: Sequence[Tuple[str, Gripper]],
        derived_gripper_lines: Sequence[str],
    ) -> str:
        lines = [
            f"## Snapshot {iso}",
            "",
            "### Joint States",
        ]
        if joint_states:
            for topic, msg in joint_states:
                lines.append(f"- `{self._format_joint_state(topic, msg)}`")
        else:
            lines.append("- no joint state topic available")

        lines.extend(["", "### End Pose"])
        if poses:
            for topic, msg in poses:
                lines.append(f"- `{self._format_pose(topic, msg)}`")
        else:
            lines.append("- no FK end pose topic available")

        lines.extend(["", "### Gripper"])
        if grippers:
            for topic, msg in grippers:
                lines.append(f"- `{self._format_gripper(topic, msg)}`")
        elif derived_gripper_lines:
            for line in derived_gripper_lines:
                lines.append(f"- `{line}`")
        else:
            lines.append("- no gripper topic available")
        lines.append("")
        return "\n".join(lines)

    def snapshot_current_state(self):
        self._banner("PEDAL: STATE SNAPSHOT REQUEST")
        self._append_log("pedal_left_request", "KEY_A snapshot_state")
        self._append_state_log("snapshot_request", "left_pedal KEY_A")

        joint_candidates = [
            ("/joint_states_single", "sensor_msgs/JointState", JointState),
            ("/joint_states_single_l", "sensor_msgs/JointState", JointState),
            ("/joint_states_single_r", "sensor_msgs/JointState", JointState),
        ]
        pose_candidates = [
            ("/piper_FK/urdf_end_pose_orient", "geometry_msgs/PoseStamped", PoseStamped),
            ("/piper_FK_l/urdf_end_pose_orient", "geometry_msgs/PoseStamped", PoseStamped),
            ("/piper_FK_r/urdf_end_pose_orient", "geometry_msgs/PoseStamped", PoseStamped),
        ]
        gripper_candidates = [
            ("/sensor/gripper/data", "data_msgs/Gripper", Gripper),
            ("/sensor/gripper_l/data", "data_msgs/Gripper", Gripper),
            ("/sensor/gripper_r/data", "data_msgs/Gripper", Gripper),
            ("/gripper/gripper/data", "data_msgs/Gripper", Gripper),
            ("/gripper/gripper_l/data", "data_msgs/Gripper", Gripper),
            ("/gripper/gripper_r/data", "data_msgs/Gripper", Gripper),
        ]
        fallback_joint_candidates = [
            ("/joint_states_gripper", "sensor_msgs/JointState", JointState),
            ("/joint_states_gripper_l", "sensor_msgs/JointState", JointState),
            ("/joint_states_gripper_r", "sensor_msgs/JointState", JointState),
        ]

        joint_states = self._collect_first_available(joint_candidates, allow_multiple=True)
        poses = self._collect_first_available(pose_candidates, allow_multiple=True)
        grippers = self._collect_first_available(gripper_candidates, allow_multiple=True)
        fallback_joint_states = self._collect_first_available(fallback_joint_candidates, allow_multiple=True)

        derived_gripper_lines = []
        if not grippers:
            for topic, msg in fallback_joint_states:
                if not msg.position:
                    continue
                derived_gripper_lines.append(
                    f"{topic}: derived_gripper_joint={msg.position[-1]:.6f} from last joint position"
                )

        now = time.time()
        iso = dt.datetime.fromtimestamp(now).isoformat()
        summary_parts = [
            f"joint_topics={len(joint_states)}",
            f"fk_topics={len(poses)}",
            f"gripper_topics={len(grippers)}",
            f"derived_gripper={len(derived_gripper_lines)}",
        ]
        self._append_state_log("snapshot_result", " ".join(summary_parts))

        detail_lines = []
        for topic, msg in joint_states:
            detail_lines.append(self._format_joint_state(topic, msg))
        for topic, msg in poses:
            detail_lines.append(self._format_pose(topic, msg))
        for topic, msg in grippers:
            detail_lines.append(self._format_gripper(topic, msg))
        detail_lines.extend(derived_gripper_lines)

        for line in detail_lines:
            self._append_state_log("snapshot_data", line)

        markdown = self._build_snapshot_markdown(iso, joint_states, poses, grippers, derived_gripper_lines)
        self.state_md_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.state_md_path.exists()
        with self.state_md_path.open("a", encoding="utf-8") as file:
            if write_header:
                file.write("# Foot Pedal State Snapshots\n\n")
            file.write(markdown)

        banner_detail = "\n".join(detail_lines[:6]) if detail_lines else "No matching topics received."
        self._banner("STATE SNAPSHOT SAVED", banner_detail)
        rospy.loginfo("Left pedal snapshot saved to %s and %s", self.state_log_path, self.state_md_path)

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
        if ev_type != EV_KEY or value != KEY_PRESS:
            return
        if code == KEY_A:
            self._append_log("pedal_key_down", "KEY_A")
            self.snapshot_current_state()
            return
        if code == KEY_B:
            self._append_log("pedal_key_down", "KEY_B")
            rospy.loginfo("Middle pedal(KEY_B) pressed. No action bound.")
            return
        if code == KEY_C:
            self._append_log("pedal_key_down", "KEY_C")
            self.toggle()

    def run(self):
        rospy.init_node("foot_pedal_capture_toggle", anonymous=True)
        rospy.wait_for_service("/data_tools_dataCapture/capture_service")
        self.capture_srv = rospy.ServiceProxy("/data_tools_dataCapture/capture_service", CaptureService)
        self.open_device()
        rospy.loginfo(
            "Foot pedal capture toggle ready. Left pedal(KEY_A) snapshots state. Right pedal(KEY_C) toggles start/stop. dataset_dir=%s next_episode=episode%d",
            self.args.dataset_dir,
            self.next_episode,
        )
        self._banner(
            "FOOT PEDAL CAPTURE READY",
            (
                f"device={self.device}\n"
                "left pedal KEY_A snapshots current state\n"
                "right pedal KEY_C toggles capture\n"
                f"next episode=episode{self.next_episode}"
            ),
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
        description=(
            "Use the left foot pedal (KEY_A) to snapshot current robot state and "
            "the right foot pedal (KEY_C) to toggle ROS data capture start/stop."
        )
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
