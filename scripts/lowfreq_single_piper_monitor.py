#!/usr/bin/env python3
import math
import sys

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


def run_pose():
    state = {"fk": None, "ctrl": None}

    def cb_fk(msg):
        p = msg.pose.position
        o = msg.pose.orientation
        state["fk"] = (p.x, p.y, p.z, *q_to_rpy((o.x, o.y, o.z, o.w)))

    def cb_ctrl(msg):
        p = msg.pose.position
        o = msg.pose.orientation
        state["ctrl"] = (p.x, p.y, p.z, *q_to_rpy((o.x, o.y, o.z, o.w)))

    rospy.init_node("lowfreq_pose_monitor", anonymous=True)
    rospy.Subscriber("/piper_FK/urdf_end_pose_orient", PoseStamped, cb_fk, queue_size=1)
    rospy.Subscriber("/piper_IK/ctrl_end_pose", PoseStamped, cb_ctrl, queue_size=1)
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 80)
        print("低频位姿监控 1 Hz")
        fk = state["fk"]
        ctrl = state["ctrl"]
        if fk:
            print("FK   : x={:.4f} y={:.4f} z={:.4f} r={:.4f} p={:.4f} y={:.4f}".format(*fk))
        else:
            print("FK   : 无数据")
        if ctrl:
            print("CTRL : x={:.4f} y={:.4f} z={:.4f} r={:.4f} p={:.4f} y={:.4f}".format(*ctrl))
        else:
            print("CTRL : 无数据")
        if fk and ctrl:
            diff = [ctrl[i] - fk[i] for i in range(6)]
            print("DIFF : dx={:.4f} dy={:.4f} dz={:.4f} dr={:.4f} dp={:.4f} dy={:.4f}".format(*diff))
        sys.stdout.flush()
        rate.sleep()


def run_gripper():
    state = {"sense": None, "merged": None}

    def cb_sense(msg):
        if msg.position:
            state["sense"] = msg.position[0]

    def cb_merged(msg):
        if len(msg.position) >= 7:
            state["merged"] = msg.position[6]

    rospy.init_node("lowfreq_gripper_monitor", anonymous=True)
    rospy.Subscriber("/sensor/gripper/joint_state", JointState, cb_sense, queue_size=1)
    rospy.Subscriber("/joint_states_single_gripper", JointState, cb_merged, queue_size=1)
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 80)
        print("低频夹爪监控 1 Hz")
        if state["sense"] is None:
            print("sense 夹爪开口: 无数据")
        else:
            print("sense 夹爪开口: {:.4f} m".format(state["sense"]))
        if state["merged"] is None:
            print("合并后 joint6/7 开口: 无数据")
        else:
            print("合并后 joint6/7 开口: {:.4f} m".format(state["merged"]))
        sys.stdout.flush()
        rate.sleep()


def run_status():
    state = {"teleop": None, "arm": None, "loc": None}

    def cb_teleop(msg):
        state["teleop"] = (msg.fail, msg.quit)

    def cb_arm(msg):
        state["arm"] = msg.over_limit

    def cb_loc(msg):
        state["loc"] = msg.accurate

    rospy.init_node("lowfreq_status_monitor", anonymous=True)
    rospy.Subscriber("/teleop_status", TeleopStatus, cb_teleop, queue_size=1)
    rospy.Subscriber("/arm_control_status", ArmControlStatus, cb_arm, queue_size=1)
    rospy.Subscriber("/pika_localization_status", LocalizationStatus, cb_loc, queue_size=1)
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 80)
        print("低频状态监控 1 Hz")
        print("localization accurate:", state["loc"])
        print("teleop (fail, quit):", state["teleop"])
        print("arm over_limit:", state["arm"])
        sys.stdout.flush()
        rate.sleep()


def main():
    if len(sys.argv) != 2:
        print("用法: lowfreq_single_piper_monitor.py [pose|gripper|status]")
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "pose":
        run_pose()
    elif mode == "gripper":
        run_gripper()
    elif mode == "status":
        run_status()
    else:
        print("未知模式:", mode)
        sys.exit(1)


if __name__ == "__main__":
    main()
