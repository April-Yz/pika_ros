#!/usr/bin/env python3
"""
Inspect frame-removal decisions made by trim_static_teleop_frames.py.

This tool loads one raw teleop episode, rebuilds the aligned head-camera
timeline, and reports which frames would be removed under the current static
trimming rule. For every removed frame it compares:

- the removed frame vs the previous kept frame
- the removed frame vs the immediate previous raw frame

The comparison is reported separately for left and right arms using the same
motion-state as the trimming script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from trim_static_teleop_frames import (
    aligned_motion_state_at,
    build_paths,
    list_files,
    motion_gripper_dirs,
    timestamp,
)

ROBOT_DIM_NAMES = ["x", "y", "z", "roll", "pitch", "yaw", "robot_gripper_distance"]
SENSOR_DIM_NAMES = [
    "x",
    "y",
    "z",
    "roll",
    "pitch",
    "yaw",
    "robot_gripper_distance",
    "sensor_gripper_distance",
]


def arm_breakdown(current: np.ndarray, reference: np.ndarray, dim_names: List[str]) -> Dict[str, object]:
    delta = current - reference
    abs_delta = np.abs(delta)
    return {
        "sum_abs": float(abs_delta.sum()),
        "delta": {name: float(value) for name, value in zip(dim_names, delta)},
        "abs_delta": {name: float(value) for name, value in zip(dim_names, abs_delta)},
        "current": {name: float(value) for name, value in zip(dim_names, current)},
        "reference": {name: float(value) for name, value in zip(dim_names, reference)},
    }


def inspect_episode(episode_dir: Path, threshold: float, gripper_source: str) -> Dict[str, object]:
    paths = build_paths(episode_dir)
    head_files = list_files(paths.head_rgb, ".jpg")
    left_pose_files = list_files(paths.left_pose, ".json")
    right_pose_files = list_files(paths.right_pose, ".json")
    left_gripper_dirs, right_gripper_dirs = motion_gripper_dirs(paths, gripper_source)
    left_gripper_file_groups = [list_files(path, ".json") for path in left_gripper_dirs]
    right_gripper_file_groups = [list_files(path, ".json") for path in right_gripper_dirs]
    dim_names = SENSOR_DIM_NAMES if gripper_source == "sensor" else ROBOT_DIM_NAMES

    required = [head_files, left_pose_files, right_pose_files, *left_gripper_file_groups, *right_gripper_file_groups]
    if any(len(files) < 2 for files in required):
        raise RuntimeError("missing required files for inspection")

    timeline = [timestamp(path) for path in head_files]
    states = np.stack(
        [
            aligned_motion_state_at(
                ts,
                left_pose_files,
                right_pose_files,
                left_gripper_file_groups,
                right_gripper_file_groups,
            )
            for ts in timeline
        ],
        axis=0,
    )
    arm_dim = states.shape[1] // 2

    kept_indices = [0]
    last_kept = 0
    removed: List[Dict[str, object]] = []
    for idx in range(1, len(states) - 1):
        left_vs_kept = arm_breakdown(states[idx, :arm_dim], states[last_kept, :arm_dim], dim_names)
        right_vs_kept = arm_breakdown(states[idx, arm_dim:], states[last_kept, arm_dim:], dim_names)
        max_sum_abs = max(left_vs_kept["sum_abs"], right_vs_kept["sum_abs"])
        if max_sum_abs >= threshold:
            kept_indices.append(idx)
            last_kept = idx
            continue

        prev_raw = max(0, idx - 1)
        removed.append(
            {
                "frame_index": idx,
                "timestamp": timeline[idx],
                "previous_kept_index": last_kept,
                "previous_kept_timestamp": timeline[last_kept],
                "previous_raw_index": prev_raw,
                "previous_raw_timestamp": timeline[prev_raw],
                "threshold": threshold,
                "decision_metric_max_sum_abs": float(max_sum_abs),
                "left_vs_previous_kept": left_vs_kept,
                "right_vs_previous_kept": right_vs_kept,
                "left_vs_previous_raw": arm_breakdown(states[idx, :arm_dim], states[prev_raw, :arm_dim], dim_names),
                "right_vs_previous_raw": arm_breakdown(states[idx, arm_dim:], states[prev_raw, arm_dim:], dim_names),
            }
        )

    if kept_indices[-1] != len(states) - 1:
        kept_indices.append(len(states) - 1)

    return {
        "episode": episode_dir.name,
        "threshold": threshold,
        "gripper_source": gripper_source,
        "original_frames": len(states),
        "kept_frames": len(kept_indices),
        "removed_frames": len(removed),
        "kept_indices": kept_indices,
        "removed": removed,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect which frames would be removed by static-frame trimming.")
    parser.add_argument("episode_dir", help="Raw episode directory, e.g. ~/agilex/pnp_bread/good/episode147")
    parser.add_argument("--motion-threshold", type=float, required=True, help="Same threshold used in trimming")
    parser.add_argument("--gripper-source", choices=["robot", "sensor"], default="robot")
    parser.add_argument("--limit", type=int, default=20, help="How many removed frames to print. Default: 20")
    parser.add_argument("--output-json", help="Optional JSON path for full inspection report")
    return parser.parse_args()


def print_removed_frames(report: Dict[str, object], limit: int) -> None:
    removed = report["removed"]
    print(
        f"episode={report['episode']} original={report['original_frames']} "
        f"kept={report['kept_frames']} removed={report['removed_frames']} "
        f"threshold={report['threshold']}"
    )
    if not removed:
        print("no removed frames under current threshold")
        return

    for item in removed[:limit]:
        print(
            f"[removed] frame={item['frame_index']} ts={item['timestamp']:.6f} "
            f"prev_kept={item['previous_kept_index']} prev_raw={item['previous_raw_index']} "
            f"max_sum_abs={item['decision_metric_max_sum_abs']:.8f}"
        )
        print(
            f"  left vs prev_kept sum={item['left_vs_previous_kept']['sum_abs']:.8f} "
            f"right vs prev_kept sum={item['right_vs_previous_kept']['sum_abs']:.8f}"
        )
        print(
            f"  left vs prev_raw  sum={item['left_vs_previous_raw']['sum_abs']:.8f} "
            f"right vs prev_raw  sum={item['right_vs_previous_raw']['sum_abs']:.8f}"
        )
        print(f"  left abs_delta vs prev_kept  {item['left_vs_previous_kept']['abs_delta']}")
        print(f"  right abs_delta vs prev_kept {item['right_vs_previous_kept']['abs_delta']}")

    remaining = len(removed) - min(len(removed), limit)
    if remaining > 0:
        print(f"... {remaining} more removed frames not shown; raise --limit or use --output-json")


def main() -> int:
    args = parse_args()
    episode_dir = Path(args.episode_dir).expanduser().resolve()
    report = inspect_episode(episode_dir, args.motion_threshold, args.gripper_source)
    print_removed_frames(report, args.limit)

    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"saved inspection report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
