#!/usr/bin/env python3
import argparse
import json
import math

import cv2
import numpy as np


def inv_T(T):
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = T[:3, :3].T
    out[:3, 3] = -out[:3, :3].dot(T[:3, 3])
    return out


def make_T(R, t):
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = np.asarray(R, dtype=np.float64).reshape(3, 3)
    out[:3, 3] = np.asarray(t, dtype=np.float64).reshape(3)
    return out


def rot_angle_deg(R):
    v = (float(np.trace(R)) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, v))))


def transform_spread(Ts):
    if len(Ts) < 2:
        return {
            "translation_mean_m": 0.0,
            "translation_max_m": 0.0,
            "rotation_mean_deg": 0.0,
            "rotation_max_deg": 0.0,
        }
    ref = Ts[0]
    trans = []
    rots = []
    for T in Ts[1:]:
        delta = inv_T(ref).dot(T)
        trans.append(float(np.linalg.norm(delta[:3, 3])))
        rots.append(rot_angle_deg(delta[:3, :3]))
    return {
        "translation_mean_m": float(np.mean(trans)),
        "translation_max_m": float(np.max(trans)),
        "rotation_mean_deg": float(np.mean(rots)),
        "rotation_max_deg": float(np.max(rots)),
    }


def solve_eye_in_hand(base_T_gripper, camera_T_board):
    R_gripper2base = [T[:3, :3] for T in base_T_gripper]
    t_gripper2base = [T[:3, 3].reshape(3, 1) for T in base_T_gripper]
    R_target2cam = [T[:3, :3] for T in camera_T_board]
    t_target2cam = [T[:3, 3].reshape(3, 1) for T in camera_T_board]
    R_cam2gripper, t_cam2gripper = cv2.calibrateHandEye(
        R_gripper2base,
        t_gripper2base,
        R_target2cam,
        t_target2cam,
        method=cv2.CALIB_HAND_EYE_TSAI,
    )
    return make_T(R_cam2gripper, t_cam2gripper)


def residual_eye_in_hand(base_T_gripper, camera_T_board, gripper_T_camera):
    base_T_board = [
        base_T_gripper[i].dot(gripper_T_camera).dot(camera_T_board[i])
        for i in range(len(base_T_gripper))
    ]
    return transform_spread(base_T_board)


def main():
    parser = argparse.ArgumentParser(description="Diagnose saved PIKA hand-eye calibration samples.")
    parser.add_argument("samples_npz")
    parser.add_argument("--mode", choices=["eye_in_hand"], default="eye_in_hand")
    args = parser.parse_args()

    data = np.load(args.samples_npz, allow_pickle=True)
    base_T_gripper = data["base_T_gripper"]
    camera_T_board = data["camera_T_board"]
    meta = str(data["meta"]) if "meta" in data.files else "{}"

    print("samples:", len(base_T_gripper))
    print("meta:", meta)
    print("robot FK spread vs first sample:")
    print(json.dumps(transform_spread(base_T_gripper), indent=2))
    print("camera->board visual pose spread vs first sample:")
    print(json.dumps(transform_spread(camera_T_board), indent=2))
    print("robot position min:", base_T_gripper[:, :3, 3].min(axis=0).tolist())
    print("robot position max:", base_T_gripper[:, :3, 3].max(axis=0).tolist())

    robot_spread = transform_spread(base_T_gripper)
    if robot_spread["translation_max_m"] < 1e-4 and robot_spread["rotation_max_deg"] < 0.05:
        print("diagnosis: BAD DATA - robot FK is effectively constant across all samples.")
        print("reason: hand-eye calibration needs robot motion; these samples cannot be solved reliably.")
        return

    try:
        gripper_T_camera = solve_eye_in_hand(base_T_gripper, camera_T_board)
        print("gripper_T_camera:")
        print(gripper_T_camera)
        print("residual:")
        print(json.dumps(residual_eye_in_hand(base_T_gripper, camera_T_board, gripper_T_camera), indent=2))
    except Exception as exc:
        print("solve failed:", repr(exc))


if __name__ == "__main__":
    main()
