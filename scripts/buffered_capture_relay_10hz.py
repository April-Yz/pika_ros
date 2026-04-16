#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


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
    import rostopic
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import rospy
    import rostopic


TOPIC_MAPPINGS = [
    ("gripper_l_color", "/gripper/camera_l/color/image_raw", "/buffered_capture/gripper/camera_l/color/image_raw"),
    ("gripper_r_color", "/gripper/camera_r/color/image_raw", "/buffered_capture/gripper/camera_r/color/image_raw"),
    ("d435_color", "/camera/color/image_raw", "/buffered_capture/camera/color/image_raw"),
    ("gripper_l_depth", "/gripper/camera_l/aligned_depth_to_color/image_raw", "/buffered_capture/gripper/camera_l/aligned_depth_to_color/image_raw"),
    ("gripper_r_depth", "/gripper/camera_r/aligned_depth_to_color/image_raw", "/buffered_capture/gripper/camera_r/aligned_depth_to_color/image_raw"),
    ("joint_states_gripper_l", "/joint_states_gripper_l", "/buffered_capture/joint_states_gripper_l"),
    ("joint_states_gripper_r", "/joint_states_gripper_r", "/buffered_capture/joint_states_gripper_r"),
    ("joint_states_single_gripper_l", "/joint_states_single_gripper_l", "/buffered_capture/joint_states_single_gripper_l"),
    ("joint_states_single_gripper_r", "/joint_states_single_gripper_r", "/buffered_capture/joint_states_single_gripper_r"),
    ("piper_ik_l", "/piper_IK_l/receive_end_pose_orient", "/buffered_capture/piper_IK_l/receive_end_pose_orient"),
    ("piper_ik_r", "/piper_IK_r/receive_end_pose_orient", "/buffered_capture/piper_IK_r/receive_end_pose_orient"),
    ("piper_fk_l", "/piper_FK_l/urdf_end_pose_orient", "/buffered_capture/piper_FK_l/urdf_end_pose_orient"),
    ("piper_fk_r", "/piper_FK_r/urdf_end_pose_orient", "/buffered_capture/piper_FK_r/urdf_end_pose_orient"),
    ("pika_pose_l", "/pika_pose_l", "/buffered_capture/pika_pose_l"),
    ("pika_pose_r", "/pika_pose_r", "/buffered_capture/pika_pose_r"),
    ("sensor_gripper_l", "/sensor/gripper_l/data", "/buffered_capture/sensor/gripper_l/data"),
    ("sensor_gripper_r", "/sensor/gripper_r/data", "/buffered_capture/sensor/gripper_r/data"),
    ("gripper_gripper_l", "/gripper/gripper_l/data", "/buffered_capture/gripper/gripper_l/data"),
    ("gripper_gripper_r", "/gripper/gripper_r/data", "/buffered_capture/gripper/gripper_r/data"),
]


@dataclass
class TopicRelay:
    label: str
    source_topic: str
    target_topic: str
    message_class: object
    publisher: object
    subscriber: object
    latest_msg: object = None
    latest_recv_wall: float = 0.0
    recv_total: int = 0
    recv_since_log: int = 0
    pub_total: int = 0
    pub_since_log: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class BufferedCaptureRelay:
    def __init__(self, dataset_dir: str, publish_hz: float):
        self.dataset_dir = Path(dataset_dir).expanduser()
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dataset_dir / "buffered_capture_relay_10hz.log"
        self.publish_hz = publish_hz
        self.relays: Dict[str, TopicRelay] = {}
        self.last_log_wall = time.time()

    def append_log(self, record: dict):
        record.setdefault("wall_time", dt.datetime.now().isoformat())
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _make_callback(self, relay: TopicRelay):
        def _callback(msg):
            now = time.time()
            with relay.lock:
                relay.latest_msg = msg
                relay.latest_recv_wall = now
                relay.recv_total += 1
                relay.recv_since_log += 1
        return _callback

    def setup_relays(self):
        for label, source_topic, target_topic in TOPIC_MAPPINGS:
            message_class, resolved_topic, _ = rostopic.get_topic_class(source_topic, blocking=True)
            if message_class is None:
                raise RuntimeError(f"Could not resolve message type for {source_topic}")
            publisher = rospy.Publisher(target_topic, message_class, queue_size=1, tcp_nodelay=True)
            relay = TopicRelay(
                label=label,
                source_topic=resolved_topic or source_topic,
                target_topic=target_topic,
                message_class=message_class,
                publisher=publisher,
                subscriber=None,
            )
            relay.subscriber = rospy.Subscriber(
                source_topic,
                message_class,
                self._make_callback(relay),
                queue_size=1,
                tcp_nodelay=True,
            )
            self.relays[label] = relay

        self.append_log(
            {
                "event": "relay_ready",
                "publish_hz": self.publish_hz,
                "topics": [
                    {
                        "label": relay.label,
                        "source": relay.source_topic,
                        "target": relay.target_topic,
                        "type": relay.message_class.__name__,
                    }
                    for relay in self.relays.values()
                ],
            }
        )

    def publish_tick(self, _event):
        for relay in self.relays.values():
            with relay.lock:
                msg = relay.latest_msg
            if msg is None:
                continue
            relay.publisher.publish(msg)
            with relay.lock:
                relay.pub_total += 1
                relay.pub_since_log += 1

    def log_tick(self, _event):
        now = time.time()
        elapsed = max(now - self.last_log_wall, 1e-6)
        topic_stats = []
        for relay in self.relays.values():
            with relay.lock:
                recv_since = relay.recv_since_log
                pub_since = relay.pub_since_log
                recv_total = relay.recv_total
                pub_total = relay.pub_total
                age_sec = None if relay.latest_recv_wall == 0 else now - relay.latest_recv_wall
                relay.recv_since_log = 0
                relay.pub_since_log = 0
            topic_stats.append(
                {
                    "label": relay.label,
                    "source_topic": relay.source_topic,
                    "target_topic": relay.target_topic,
                    "source_hz": recv_since / elapsed,
                    "publish_hz": pub_since / elapsed,
                    "recv_total": recv_total,
                    "pub_total": pub_total,
                    "age_sec": age_sec,
                }
            )
        self.last_log_wall = now
        self.append_log({"event": "relay_status", "topics": topic_stats})

    def run(self):
        rospy.init_node("buffered_capture_relay_10hz", anonymous=True)
        self.setup_relays()
        rospy.Timer(rospy.Duration(1.0 / self.publish_hz), self.publish_tick)
        rospy.Timer(rospy.Duration(1.0), self.log_tick)
        rospy.loginfo("Buffered capture relay ready. publish_hz=%.2f log=%s", self.publish_hz, self.log_path)
        rospy.spin()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Republish non-fisheye capture topics at a fixed rate using the latest received message."
    )
    parser.add_argument("--dataset-dir", default=os.path.expanduser("~/agilex/data"))
    parser.add_argument("--publish-hz", type=float, default=10.0)
    return parser.parse_args()


def main():
    args = parse_args()
    relay = BufferedCaptureRelay(args.dataset_dir, args.publish_hz)
    relay.run()


if __name__ == "__main__":
    raise SystemExit(main())
