#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import json
import os
import sys
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
    from data_msgs.msg import CaptureStatus
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import rospy
    from data_msgs.msg import CaptureStatus


class CaptureStatusHzLogger:
    def __init__(self, dataset_dir: str, output_name: str):
        self.dataset_dir = Path(dataset_dir).expanduser()
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.dataset_dir / output_name

    def callback(self, msg: CaptureStatus):
        wall = dt.datetime.now().isoformat()
        ros_now = rospy.Time.now().to_sec()
        record = {
            "wall_time": wall,
            "ros_time": ros_now,
            "fail": bool(msg.fail),
            "quit": bool(msg.quit),
            "topics": list(msg.topics),
            "count_in_seconds": list(msg.count_in_seconds),
            "frequencies": [float(x) for x in msg.frequencies],
        }
        with self.output_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

    def run(self):
        rospy.init_node("capture_status_hz_logger", anonymous=True)
        rospy.Subscriber("/data_tools_dataCapture/status", CaptureStatus, self.callback, queue_size=100)
        rospy.loginfo("Writing capture status hz log to: %s", self.output_path)
        rospy.spin()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Log /data_tools_dataCapture/status to a JSONL file for later timing and hz analysis."
    )
    parser.add_argument("--dataset-dir", default=os.path.expanduser("~/agilex/data"))
    parser.add_argument("--output-name", default="capture_status_hz.log")
    return parser.parse_args()


def main():
    args = parse_args()
    CaptureStatusHzLogger(args.dataset_dir, args.output_name).run()


if __name__ == "__main__":
    raise SystemExit(main())
