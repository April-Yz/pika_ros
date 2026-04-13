#!/usr/bin/env python3
import math
import statistics
import sys
import time

import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState

from data_msgs.msg import ArmControlStatus, LocalizationStatus, TeleopStatus


def q_to_rpy(q):
    x, y, z, w = q
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def vec_norm(values):
    return math.sqrt(sum(v * v for v in values))


class TopicStats:
    def __init__(self, name):
        self.name = name
        self.last_recv = None
        self.last_header = None
        self.last_value = None
        self.curr_value = None
        self.intervals = []
        self.max_samples = 80

    def update(self, header_stamp_sec, value):
        now = time.time()
        if self.last_recv is not None:
            self.intervals.append(now - self.last_recv)
            if len(self.intervals) > self.max_samples:
                self.intervals.pop(0)
        self.last_recv = now
        self.last_header = header_stamp_sec
        self.last_value = self.curr_value
        self.curr_value = value

    def age_ms(self):
        if self.last_header is None:
            return None
        return max(0.0, (time.time() - self.last_header) * 1000.0)

    def hz(self):
        if not self.intervals:
            return None
        avg = sum(self.intervals) / len(self.intervals)
        if avg <= 0:
            return None
        return 1.0 / avg

    def jitter_ms(self):
        if len(self.intervals) < 2:
            return None
        return statistics.pstdev(self.intervals) * 1000.0

    def step(self):
        if self.last_value is None or self.curr_value is None:
            return None
        return vec_norm([a - b for a, b in zip(self.curr_value, self.last_value)])


def fmt_num(value, unit="", width=7, precision=2):
    if value is None:
        return " " * (width - 2) + "--"
    return f"{value:{width}.{precision}f}{unit}"


def pose_tuple(msg):
    p = msg.pose.position
    o = msg.pose.orientation
    return (p.x, p.y, p.z, *q_to_rpy((o.x, o.y, o.z, o.w)))


def run_pose():
    pika = TopicStats("PIKA")
    ctrl = TopicStats("CTRL")
    fk = TopicStats("FK")
    loc = {"accurate": None}
    teleop = {"state": None}
    arm = {"over_limit": None}

    def cb_pika(msg):
        pika.update(msg.header.stamp.to_sec(), pose_tuple(msg))

    def cb_ctrl(msg):
        ctrl.update(msg.header.stamp.to_sec(), pose_tuple(msg))

    def cb_fk(msg):
        fk.update(msg.header.stamp.to_sec(), pose_tuple(msg))

    def cb_loc(msg):
        loc["accurate"] = msg.accurate

    def cb_teleop(msg):
        teleop["state"] = (msg.fail, msg.quit)

    def cb_arm(msg):
        arm["over_limit"] = msg.over_limit

    rospy.init_node("single_piper_jitter_pose_probe", anonymous=True)
    rospy.Subscriber("/pika_pose", PoseStamped, cb_pika, queue_size=1)
    rospy.Subscriber("/piper_IK/ctrl_end_pose", PoseStamped, cb_ctrl, queue_size=1)
    rospy.Subscriber("/piper_FK/urdf_end_pose_orient", PoseStamped, cb_fk, queue_size=1)
    rospy.Subscriber("/pika_localization_status", LocalizationStatus, cb_loc, queue_size=1)
    rospy.Subscriber("/teleop_status", TeleopStatus, cb_teleop, queue_size=1)
    rospy.Subscriber("/arm_control_status", ArmControlStatus, cb_arm, queue_size=1)

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 96)
        print("单臂遥操抖动探针 1 Hz")
        print(
            "状态: localization={} teleop={} over_limit={}".format(
                loc["accurate"], teleop["state"], arm["over_limit"]
            )
        )
        print("主题   age_ms   hz   jitter_ms   step_poserpy")
        for item in (pika, ctrl, fk):
            print(
                "{:<5} {} {} {} {}".format(
                    item.name,
                    fmt_num(item.age_ms(), width=8),
                    fmt_num(item.hz(), width=6),
                    fmt_num(item.jitter_ms(), width=11),
                    fmt_num(item.step(), width=12, precision=4),
                )
            )
        if pika.curr_value:
            print(
                "PIKA : x={:.4f} y={:.4f} z={:.4f} r={:.4f} p={:.4f} y={:.4f}".format(
                    *pika.curr_value
                )
            )
        else:
            print("PIKA : 无数据")
        if ctrl.curr_value:
            print(
                "CTRL : x={:.4f} y={:.4f} z={:.4f} r={:.4f} p={:.4f} y={:.4f}".format(
                    *ctrl.curr_value
                )
            )
        else:
            print("CTRL : 无数据")
        if fk.curr_value:
            print(
                "FK   : x={:.4f} y={:.4f} z={:.4f} r={:.4f} p={:.4f} y={:.4f}".format(
                    *fk.curr_value
                )
            )
        else:
            print("FK   : 无数据")
        if ctrl.curr_value and fk.curr_value:
            diff = [ctrl.curr_value[i] - fk.curr_value[i] for i in range(6)]
            print(
                "CTRL-FK : dx={:.4f} dy={:.4f} dz={:.4f} dr={:.4f} dp={:.4f} dy={:.4f}".format(
                    *diff
                )
            )
        else:
            print("CTRL-FK : 无法比较")
        sys.stdout.flush()
        rate.sleep()


def run_gripper():
    sense = TopicStats("SENSE")
    merged = TopicStats("MERGED")
    joint = TopicStats("JOINT7")

    def cb_sense(msg):
        if msg.position:
            sense.update(msg.header.stamp.to_sec(), (msg.position[0],))

    def cb_merged(msg):
        if len(msg.position) >= 7:
            merged.update(msg.header.stamp.to_sec(), (msg.position[6],))

    def cb_joint(msg):
        if len(msg.position) >= 7:
            joint.update(msg.header.stamp.to_sec(), (msg.position[6],))

    rospy.init_node("single_piper_jitter_gripper_probe", anonymous=True)
    rospy.Subscriber("/sensor/gripper/joint_state", JointState, cb_sense, queue_size=1)
    rospy.Subscriber("/joint_states_single_gripper", JointState, cb_merged, queue_size=1)
    rospy.Subscriber("/joint_states_single", JointState, cb_joint, queue_size=1)

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 96)
        print("单臂夹爪抖动探针 1 Hz")
        print("主题    age_ms   hz   jitter_ms   step_opening")
        for item in (sense, merged, joint):
            print(
                "{:<6} {} {} {} {}".format(
                    item.name,
                    fmt_num(item.age_ms(), width=8),
                    fmt_num(item.hz(), width=6),
                    fmt_num(item.jitter_ms(), width=11),
                    fmt_num(item.step(), width=12, precision=5),
                )
            )
        print(
            "开口: sense={} merged={} real_joint7={}".format(
                fmt_num(sense.curr_value[0], width=8, precision=5) if sense.curr_value else "--",
                fmt_num(merged.curr_value[0], width=8, precision=5) if merged.curr_value else "--",
                fmt_num(joint.curr_value[0], width=8, precision=5) if joint.curr_value else "--",
            )
        )
        sys.stdout.flush()
        rate.sleep()


def main():
    if len(sys.argv) != 2:
        print("用法: single_piper_jitter_probe.py [pose|gripper]")
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "pose":
        run_pose()
    elif mode == "gripper":
        run_gripper()
    else:
        print("未知模式:", mode)
        sys.exit(1)


if __name__ == "__main__":
    main()
