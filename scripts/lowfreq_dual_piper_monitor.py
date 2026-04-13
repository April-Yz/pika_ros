#!/usr/bin/env python3
import math
import sys

import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState

from data_msgs.msg import ArmControlStatus, TeleopStatus


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


def pose_tuple(msg):
    p = msg.pose.position
    o = msg.pose.orientation
    return (p.x, p.y, p.z, *q_to_rpy((o.x, o.y, o.z, o.w)))


def print_pose_block(label, fk, ctrl):
    print("-" * 96)
    print(label)
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
    else:
        print("DIFF : 无法比较")


def run_pose():
    state = {"fk_l": None, "ctrl_l": None, "fk_r": None, "ctrl_r": None}

    rospy.init_node("lowfreq_dual_pose_monitor", anonymous=True)
    rospy.Subscriber("/piper_FK_l/urdf_end_pose_orient", PoseStamped, lambda msg: state.__setitem__("fk_l", pose_tuple(msg)), queue_size=1)
    rospy.Subscriber("/piper_IK_l/ctrl_end_pose", PoseStamped, lambda msg: state.__setitem__("ctrl_l", pose_tuple(msg)), queue_size=1)
    rospy.Subscriber("/piper_FK_r/urdf_end_pose_orient", PoseStamped, lambda msg: state.__setitem__("fk_r", pose_tuple(msg)), queue_size=1)
    rospy.Subscriber("/piper_IK_r/ctrl_end_pose", PoseStamped, lambda msg: state.__setitem__("ctrl_r", pose_tuple(msg)), queue_size=1)

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 96)
        print("双臂低频位姿监控 1 Hz")
        print_pose_block("LEFT", state["fk_l"], state["ctrl_l"])
        print_pose_block("RIGHT", state["fk_r"], state["ctrl_r"])
        sys.stdout.flush()
        rate.sleep()


def run_gripper():
    state = {"joint_l": None, "joint_r": None}

    def cb_l(msg):
        if len(msg.position) >= 7:
            state["joint_l"] = msg.position[6]

    def cb_r(msg):
        if len(msg.position) >= 7:
            state["joint_r"] = msg.position[6]

    rospy.init_node("lowfreq_dual_gripper_monitor", anonymous=True)
    rospy.Subscriber("/joint_states_gripper_l", JointState, cb_l, queue_size=1)
    rospy.Subscriber("/joint_states_gripper_r", JointState, cb_r, queue_size=1)

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 96)
        print("双臂低频夹爪监控 1 Hz")
        if state["joint_l"] is None:
            print("LEFT  gripper: 无数据")
        else:
            print("LEFT  gripper: {:.4f} m".format(state["joint_l"]))
        if state["joint_r"] is None:
            print("RIGHT gripper: 无数据")
        else:
            print("RIGHT gripper: {:.4f} m".format(state["joint_r"]))
        sys.stdout.flush()
        rate.sleep()


def run_status():
    state = {"teleop_l": None, "teleop_r": None, "arm_l": None, "arm_r": None}

    def cb_teleop_l(msg):
        state["teleop_l"] = (msg.fail, msg.quit)

    def cb_teleop_r(msg):
        state["teleop_r"] = (msg.fail, msg.quit)

    def cb_arm_l(msg):
        state["arm_l"] = msg.over_limit

    def cb_arm_r(msg):
        state["arm_r"] = msg.over_limit

    rospy.init_node("lowfreq_dual_status_monitor", anonymous=True)
    rospy.Subscriber("/teleop_status_l", TeleopStatus, cb_teleop_l, queue_size=1)
    rospy.Subscriber("/teleop_status_r", TeleopStatus, cb_teleop_r, queue_size=1)
    rospy.Subscriber("/arm_control_status_l", ArmControlStatus, cb_arm_l, queue_size=1)
    rospy.Subscriber("/arm_control_status_r", ArmControlStatus, cb_arm_r, queue_size=1)

    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        print("=" * 96)
        print("双臂低频状态监控 1 Hz")
        print("LEFT  teleop (fail, quit):", state["teleop_l"])
        print("LEFT  arm over_limit     :", state["arm_l"])
        print("RIGHT teleop (fail, quit):", state["teleop_r"])
        print("RIGHT arm over_limit     :", state["arm_r"])
        sys.stdout.flush()
        rate.sleep()


def main():
    if len(sys.argv) != 2:
        print("用法: lowfreq_dual_piper_monitor.py [pose|gripper|status]")
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
