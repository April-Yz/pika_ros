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


def make_T(R, t):
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = R
    out[:3, 3] = np.asarray(t, dtype=np.float64).reshape(3)
    return out


def T_to_dict(T):
    qx, qy, qz, qw = rot_to_quat(T[:3, :3])
    return {
        "translation": {"x": float(T[0, 3]), "y": float(T[1, 3]), "z": float(T[2, 3])},
        "rotation_quaternion_xyzw": {"x": float(qx), "y": float(qy), "z": float(qz), "w": float(qw)},
        "matrix": T.tolist(),
    }


def rot_angle_deg(R):
    v = (float(np.trace(R)) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, v))))


def average_transforms(Ts):
    quats = []
    for T in Ts:
        q = rot_to_quat(T[:3, :3])
        if quats and np.dot(q, quats[0]) < 0:
            q = -q
        quats.append(q)
    q = np.mean(np.stack(quats), axis=0)
    q = q / np.linalg.norm(q)
    R = quat_to_rot(q[0], q[1], q[2], q[3])
    t = np.mean(np.stack([T[:3, 3] for T in Ts]), axis=0)
    return make_T(R, t)


def spread(Ts, avg):
    trans = []
    rots = []
    for T in Ts:
        delta = inv_T(avg).dot(T)
        trans.append(float(np.linalg.norm(delta[:3, 3])))
        rots.append(rot_angle_deg(delta[:3, :3]))
    return {
        "translation_mean_m": float(np.mean(trans)),
        "translation_max_m": float(np.max(trans)),
        "rotation_mean_deg": float(np.mean(rots)),
        "rotation_max_deg": float(np.max(rots)),
    }


def load_handeye(path):
    with open(path) as f:
        data = json.load(f)
    return np.asarray(data["gripper_T_camera"]["matrix"], dtype=np.float64), data


def main():
    parser = argparse.ArgumentParser(description="Estimate left_base_T_right_base from left/right wrist hand-eye results and sample npz files.")
    parser.add_argument("--left-handeye", required=True)
    parser.add_argument("--left-samples", required=True)
    parser.add_argument("--right-handeye", required=True)
    parser.add_argument("--right-samples", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    left_gripper_T_camera, left_meta = load_handeye(args.left_handeye)
    right_gripper_T_camera, right_meta = load_handeye(args.right_handeye)
    left_samples = np.load(args.left_samples, allow_pickle=True)
    right_samples = np.load(args.right_samples, allow_pickle=True)

    left_boards = [
        left_samples["base_T_gripper"][i].dot(left_gripper_T_camera).dot(left_samples["camera_T_board"][i])
        for i in range(len(left_samples["base_T_gripper"]))
    ]
    right_boards = [
        right_samples["base_T_gripper"][i].dot(right_gripper_T_camera).dot(right_samples["camera_T_board"][i])
        for i in range(len(right_samples["base_T_gripper"]))
    ]

    left_base_T_board = average_transforms(left_boards)
    right_base_T_board = average_transforms(right_boards)
    left_base_T_right_base = left_base_T_board.dot(inv_T(right_base_T_board))

    result = {
        "left_base_T_right_base": T_to_dict(left_base_T_right_base),
        "left_base_T_board_avg": T_to_dict(left_base_T_board),
        "right_base_T_board_avg": T_to_dict(right_base_T_board),
        "left_board_spread": spread(left_boards, left_base_T_board),
        "right_board_spread": spread(right_boards, right_base_T_board),
        "inputs": {
            "left_handeye": args.left_handeye,
            "left_samples": args.left_samples,
            "right_handeye": args.right_handeye,
            "right_samples": args.right_samples,
            "left_sample_count": int(len(left_boards)),
            "right_sample_count": int(len(right_boards)),
            "left_handeye_residuals": left_meta.get("residuals", {}),
            "right_handeye_residuals": right_meta.get("residuals", {}),
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        print("saved:", args.output)


if __name__ == "__main__":
    main()
