#!/usr/bin/env /usr/bin/python3

import argparse
import os
import signal
import sys
import time

import rospy
from data_msgs.msg import TeleopStatus
from data_msgs.srv import CaptureService, CaptureServiceRequest


class DualTeleopCaptureSync:
    def __init__(self, args):
        self.args = args
        self.left_status = None
        self.right_status = None
        self.recording = False
        self.last_both_active_at = None
        self.last_not_both_active_at = None
        self.capture_srv = None
        self.next_episode = self._find_next_episode(args.dataset_dir)

    @staticmethod
    def _find_next_episode(dataset_dir):
        max_idx = -1
        if os.path.isdir(dataset_dir):
            for entry in os.listdir(dataset_dir):
                if not entry.startswith("episode"):
                    continue
                suffix = entry[len("episode") :]
                if suffix.isdigit():
                    max_idx = max(max_idx, int(suffix))
        return max_idx + 1

    @staticmethod
    def _status_active(status):
        return status is not None and (not status.fail) and (not status.quit)

    def _both_active(self):
        return self._status_active(self.left_status) and self._status_active(self.right_status)

    def _teleop_cb_l(self, msg):
        self.left_status = msg

    def _teleop_cb_r(self, msg):
        self.right_status = msg

    def _call_capture(self, start, end, episode_index):
        req = CaptureServiceRequest()
        req.start = start
        req.end = end
        req.episode_index = episode_index
        req.dataset_dir = self.args.dataset_dir
        req.instructions = self.args.instructions
        return self.capture_srv(req)

    def start_recording(self):
        if self.recording:
            return
        rospy.loginfo(
            "Starting capture for episode%d because both teleop states are active.",
            self.next_episode,
        )
        res = self._call_capture(True, False, self.next_episode)
        if not res.success:
            rospy.logerr("Failed to start capture: %s", res.message)
            return
        self.recording = True
        self.next_episode += 1

    def stop_recording(self):
        if not self.recording:
            return
        rospy.loginfo("Stopping capture because dual teleop is no longer jointly active.")
        res = self._call_capture(False, True, -1)
        if not res.success:
            rospy.logerr("Failed to stop capture: %s", res.message)
            return
        self.recording = False

    def run(self):
        rospy.init_node("dual_teleop_capture_sync", anonymous=True)
        rospy.Subscriber("/teleop_status_l", TeleopStatus, self._teleop_cb_l, queue_size=1)
        rospy.Subscriber("/teleop_status_r", TeleopStatus, self._teleop_cb_r, queue_size=1)
        rospy.wait_for_service("/data_tools_dataCapture/capture_service")
        self.capture_srv = rospy.ServiceProxy("/data_tools_dataCapture/capture_service", CaptureService)

        rospy.loginfo(
            "Dual teleop capture sync ready. dataset_dir=%s next_episode=episode%d stable_sec=%.2f",
            self.args.dataset_dir,
            self.next_episode,
            self.args.stable_sec,
        )

        rate = rospy.Rate(20)
        while not rospy.is_shutdown():
            now = time.monotonic()
            if self._both_active():
                self.last_not_both_active_at = None
                if self.last_both_active_at is None:
                    self.last_both_active_at = now
                if (not self.recording) and now - self.last_both_active_at >= self.args.stable_sec:
                    self.start_recording()
            else:
                self.last_both_active_at = None
                if self.last_not_both_active_at is None:
                    self.last_not_both_active_at = now
                if self.recording and now - self.last_not_both_active_at >= self.args.stable_sec:
                    self.stop_recording()
            rate.sleep()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Start capture only when both teleop_status_l and teleop_status_r are active."
    )
    parser.add_argument("--dataset-dir", default=os.path.expanduser("~/agilex/data"))
    parser.add_argument("--instructions", default="[null]")
    parser.add_argument("--stable-sec", type=float, default=0.3)
    return parser.parse_args()


def main():
    args = parse_args()
    sync = DualTeleopCaptureSync(args)

    def _shutdown(*_args):
        try:
            sync.stop_recording()
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    sync.run()


if __name__ == "__main__":
    sys.exit(main())
