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
        self.next_retry_at = 0.0

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

    def _can_retry(self, now):
        return now >= self.next_retry_at

    def _delay_retry(self, now):
        self.next_retry_at = now + self.args.retry_sec

    def start_recording(self):
        if self.recording:
            return True
        rospy.loginfo(
            "Both teleop sides are active. Requesting capture start for episode%d.",
            self.next_episode,
        )
        try:
            res = self._call_capture(True, False, self.next_episode)
        except Exception as exc:
            rospy.logwarn(
                "Capture start request failed: %s. Sync monitor will keep running and retry in %.1fs.",
                exc,
                self.args.retry_sec,
            )
            return False
        if not res.success:
            rospy.logwarn(
                "Capture start was rejected: %s. Sync monitor will keep running and retry in %.1fs.",
                res.message,
                self.args.retry_sec,
            )
            return False
        self.recording = True
        self.next_episode += 1
        self.next_retry_at = 0.0
        rospy.loginfo("Capture start accepted. Recording is now active.")
        return True

    def stop_recording(self):
        if not self.recording:
            return True
        rospy.loginfo("Dual teleop is no longer jointly active. Requesting capture stop.")
        try:
            res = self._call_capture(False, True, -1)
        except Exception as exc:
            rospy.logwarn(
                "Capture stop request failed: %s. Assuming recorder is unavailable and keeping sync monitor alive.",
                exc,
            )
            self.recording = False
            return False
        if not res.success:
            rospy.logwarn(
                "Capture stop was rejected: %s. Sync monitor will continue running.",
                res.message,
            )
            self.recording = False
            return False
        self.recording = False
        self.next_retry_at = 0.0
        rospy.loginfo("Capture stop accepted. Recording is now inactive.")
        return True

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
                if (not self.recording) and now - self.last_both_active_at >= self.args.stable_sec and self._can_retry(now):
                    if not self.start_recording():
                        self._delay_retry(now)
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
    parser.add_argument("--retry-sec", type=float, default=2.0)
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
