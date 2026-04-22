#!/usr/bin/env python3
import argparse
import json
import math
import os

import numpy as np


def quat_to_rot(qx, qy, qz, qw):
    n = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    qx, qy, qz, qw = qx / n, qy / n, qz / n, qw / n
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ], dtype=np.float64)


def rot_to_quat(R):
    tr = float(np.trace(R))
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s
    q = np.array([qx, qy, qz, qw], dtype=np.float64)
    return q / np.linalg.norm(q)


def inv_T(T):
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = T[:3, :3].T
    out[:3, 3] = -out[:3, :3].dot(T[:3, 3])
    return out


def T_to_dict(T):
    qx, qy, qz, qw = rot_to_quat(T[:3, :3])
    return {
        "translation": {
            "x": float(T[0, 3]),
            "y": float(T[1, 3]),
            "z": float(T[2, 3]),
        },
        "rotation_quaternion_xyzw": {
            "x": float(qx),
            "y": float(qy),
            "z": float(qz),
            "w": float(qw),
        },
        "matrix": T.tolist(),
    }


def load_json(path):
    with open(path) as f:
        return json.load(f)


def matrix_from(data, key):
    return np.asarray(data[key]["matrix"], dtype=np.float64)


def main():
    parser = argparse.ArgumentParser(description="Export a single JSON bundle from PIKA hand-eye calibration results.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--left-handeye", required=True)
    parser.add_argument("--right-handeye", required=True)
    parser.add_argument("--base-transform", required=True)
    parser.add_argument("--head-handeye", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    left = load_json(args.left_handeye)
    right = load_json(args.right_handeye)
    base = load_json(args.base_transform)
    head = load_json(args.head_handeye)

    left_gripper_T_left_camera = matrix_from(left, "gripper_T_camera")
    right_gripper_T_right_camera = matrix_from(right, "gripper_T_camera")
    left_base_T_right_base = matrix_from(base, "left_base_T_right_base")
    left_base_T_head_camera = matrix_from(head, "left_base_T_head_camera")
    right_base_T_left_base = inv_T(left_base_T_right_base)
    right_base_T_head_camera = right_base_T_left_base.dot(left_base_T_head_camera)

    bundle = {
        "name": args.name,
        "note": args.note,
        "frames": {
            "left_base": "left arm FK base frame",
            "right_base": "right arm FK base frame",
            "left_gripper": "left /piper_FK_l/urdf_end_pose_orient frame",
            "right_gripper": "right /piper_FK_r/urdf_end_pose_orient frame",
            "left_wrist_camera": "left wrist color optical frame",
            "right_wrist_camera": "right wrist color optical frame",
            "head_camera": "D435 color optical frame",
        },
        "transforms": {
            "left_gripper_T_left_wrist_camera": T_to_dict(left_gripper_T_left_camera),
            "left_wrist_camera_T_left_gripper": T_to_dict(inv_T(left_gripper_T_left_camera)),
            "right_gripper_T_right_wrist_camera": T_to_dict(right_gripper_T_right_camera),
            "right_wrist_camera_T_right_gripper": T_to_dict(inv_T(right_gripper_T_right_camera)),
            "left_base_T_right_base": T_to_dict(left_base_T_right_base),
            "right_base_T_left_base": T_to_dict(right_base_T_left_base),
            "left_base_T_head_camera": T_to_dict(left_base_T_head_camera),
            "head_camera_T_left_base": T_to_dict(inv_T(left_base_T_head_camera)),
            "right_base_T_head_camera": T_to_dict(right_base_T_head_camera),
            "head_camera_T_right_base": T_to_dict(inv_T(right_base_T_head_camera)),
        },
        "usage": {
            "left_wrist_point_to_left_base": "P_left_base = T_left_base_left_gripper * left_gripper_T_left_wrist_camera * P_left_wrist_camera",
            "right_wrist_point_to_left_base": "P_left_base = left_base_T_right_base * T_right_base_right_gripper * right_gripper_T_right_wrist_camera * P_right_wrist_camera",
            "head_point_to_left_base": "P_left_base = left_base_T_head_camera * P_head_camera",
            "head_point_to_right_base": "P_right_base = right_base_T_head_camera * P_head_camera",
        },
        "quality": {
            "left_wrist_residuals": left.get("residuals", {}),
            "right_wrist_residuals": right.get("residuals", {}),
            "base_transform_spread": {
                "left_board_spread": base.get("left_board_spread", {}),
                "right_board_spread": base.get("right_board_spread", {}),
            },
            "head_residuals": head.get("residuals", {}),
        },
        "sources": {
            "left_handeye": args.left_handeye,
            "right_handeye": args.right_handeye,
            "base_transform": args.base_transform,
            "head_handeye": args.head_handeye,
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(bundle, f, indent=2, sort_keys=True)
    print("saved:", args.output)


if __name__ == "__main__":
    main()
