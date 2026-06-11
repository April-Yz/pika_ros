#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List


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


RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"


class CaptureRequiredTopicsWarning:
    def __init__(self, dataset_dir: str, required_topics: List[str], grace_callbacks: int):
        self.dataset_dir = Path(dataset_dir).expanduser()
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.required_topics = required_topics
        self.grace_callbacks = max(grace_callbacks, 0)
        self.callback_count = 0
        self.active_alerts = set()
        self.log_path = self.dataset_dir / "capture_required_topics_warning.log"

    def _append_log(self, record: dict):
        record.setdefault("wall_time", dt.datetime.now().isoformat())
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

    @staticmethod
    def _topic_stats(msg: CaptureStatus) -> Dict[str, dict]:
        stats = {}
        size = min(len(msg.topics), len(msg.count_in_seconds), len(msg.frequencies))
        for idx in range(size):
            stats[msg.topics[idx]] = {
                "count_in_seconds": int(msg.count_in_seconds[idx]),
                "frequency": float(msg.frequencies[idx]),
            }
        return stats

    def _missing_topics(self, msg: CaptureStatus) -> List[dict]:
        stats = self._topic_stats(msg)
        missing = []
        for topic in self.required_topics:
            topic_stat = stats.get(topic)
            if topic_stat is None:
                missing.append({"topic": topic, "reason": "topic_not_reported"})
                continue
            freq = topic_stat["frequency"]
            count = topic_stat["count_in_seconds"]
            if count <= 0:
                missing.append({"topic": topic, "reason": "count_in_seconds_zero", "count_in_seconds": count, "frequency": freq})
            elif not math.isfinite(freq):
                missing.append({"topic": topic, "reason": "frequency_not_finite", "count_in_seconds": count, "frequency": freq})
        return missing

    def callback(self, msg: CaptureStatus):
        self.callback_count += 1
        if bool(msg.quit):
            if self.active_alerts:
                print(f"{GREEN}[capture-warning] capture finished, clear previous alerts{RESET}", flush=True)
            self.active_alerts.clear()
            self._append_log({"event": "capture_quit"})
            return

        if self.callback_count <= self.grace_callbacks:
            return

        missing = self._missing_topics(msg)
        current_alerts = {item["topic"] for item in missing}

        if missing and current_alerts != self.active_alerts:
            detail = ", ".join(f"{item['topic']} ({item['reason']})" for item in missing)
            print(f"{RED}[S5 WARNING] capture started but required topics are missing: {detail}{RESET}", flush=True)
            self._append_log({"event": "missing_required_topics", "missing": missing})
        elif self.active_alerts:
            print(f"{YELLOW}[capture-warning] required topics recovered{RESET}", flush=True)
            self._append_log({"event": "required_topics_recovered"})

        self.active_alerts = current_alerts

    def run(self):
        rospy.init_node("capture_required_topics_warning", anonymous=True)
        rospy.Subscriber("/data_tools_dataCapture/status", CaptureStatus, self.callback, queue_size=100)
        rospy.loginfo("Watching capture status for required topics. log=%s", self.log_path)
        rospy.spin()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Print a red warning when capture is running but required topics are missing from CaptureStatus."
    )
    parser.add_argument("--dataset-dir", default=os.path.expanduser("~/agilex/data"))
    parser.add_argument("--require-topic", action="append", default=[])
    parser.add_argument("--grace-callbacks", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.require_topic:
        raise SystemExit("At least one --require-topic is required")
    monitor = CaptureRequiredTopicsWarning(
        dataset_dir=args.dataset_dir,
        required_topics=args.require_topic,
        grace_callbacks=args.grace_callbacks,
    )
    monitor.run()


if __name__ == "__main__":
    raise SystemExit(main())
