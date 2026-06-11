#!/usr/bin/env python3
"""
Summarize per-episode state ranges for raw teleop data.

The script aligns each episode on the head-camera timeline, rebuilds the same
14D state used by process_data_robotwin_headcam.py, and reports per-dimension
min/max/span. It supports both robot and sensor gripper sources.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from process_data_robotwin_headcam import (
    build_episode_paths,
    list_timestamped_files,
    load_gripper_json,
    load_pose_json,
    nearest_path,
    parse_timestamp_from_name,
    selected_gripper_paths,
)


DIM_NAMES = [
    "left_x",
    "left_y",
    "left_z",
    "left_roll",
    "left_pitch",
    "left_yaw",
    "left_gripper",
    "right_x",
    "right_y",
    "right_z",
    "right_roll",
    "right_pitch",
    "right_yaw",
    "right_gripper",
]


def episode_sort_key(path: Path):
    suffix = path.name[len("episode") :]
    return (0, int(suffix)) if suffix.isdigit() else (1, path.name)


def list_episode_dirs(root: Path) -> List[Path]:
    return sorted(
        [path for path in root.iterdir() if path.is_dir() and path.name.startswith("episode")],
        key=episode_sort_key,
    )


def aligned_states_for_episode(episode_dir: Path, gripper_source: str) -> np.ndarray:
    paths = build_episode_paths(episode_dir)
    head_files = list_timestamped_files(paths.head_rgb, ".jpg")
    left_pose_files = list_timestamped_files(paths.puppet_left_pose, ".json")
    right_pose_files = list_timestamped_files(paths.puppet_right_pose, ".json")
    left_gripper_dir, right_gripper_dir = selected_gripper_paths(paths, gripper_source)
    left_gripper_files = list_timestamped_files(left_gripper_dir, ".json")
    right_gripper_files = list_timestamped_files(right_gripper_dir, ".json")

    required = [head_files, left_pose_files, right_pose_files, left_gripper_files, right_gripper_files]
    if any(len(files) == 0 for files in required):
        raise RuntimeError("missing required files")

    states: List[np.ndarray] = []
    for head_path in head_files:
        ts = parse_timestamp_from_name(head_path)
        left_pose = load_pose_json(nearest_path(left_pose_files, ts))
        right_pose = load_pose_json(nearest_path(right_pose_files, ts))
        left_gripper = load_gripper_json(nearest_path(left_gripper_files, ts))
        right_gripper = load_gripper_json(nearest_path(right_gripper_files, ts))
        states.append(np.concatenate([left_pose, left_gripper, right_pose, right_gripper]).astype(np.float32))
    return np.stack(states, axis=0)


def summarize_states(states: np.ndarray) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for idx, name in enumerate(DIM_NAMES):
        values = states[:, idx]
        vmin = float(values.min())
        vmax = float(values.max())
        summary[name] = {"min": vmin, "max": vmax, "span": vmax - vmin}
    return summary


def print_episode_summary(episode_name: str, summary: Dict[str, Dict[str, float]], compact: bool) -> None:
    if compact:
        left_gripper = summary["left_gripper"]
        right_gripper = summary["right_gripper"]
        print(
            f"{episode_name}: "
            f"L_gripper[{left_gripper['min']:.6f}, {left_gripper['max']:.6f}] span={left_gripper['span']:.6f} | "
            f"R_gripper[{right_gripper['min']:.6f}, {right_gripper['max']:.6f}] span={right_gripper['span']:.6f}"
        )
        return

    print(episode_name)
    for name in DIM_NAMES:
        item = summary[name]
        print(f"  {name:>13}: min={item['min']:.6f} max={item['max']:.6f} span={item['span']:.6f}")


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize per-episode 14D state ranges for raw teleop episodes.")
    parser.add_argument("dataset_root", help="Task root, e.g. ~/agilex/pnp_bread")
    parser.add_argument("--episode-subdir", default="good", help="Episode subdir under task root. Default: good")
    parser.add_argument("--gripper-source", choices=["robot", "sensor"], default="robot")
    parser.add_argument("--episode", type=int, action="append", help="Only summarize specific episode indices")
    parser.add_argument("--compact", action="store_true", help="Only print left/right gripper ranges")
    parser.add_argument("--output-json", help="Optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_root = Path(args.dataset_root).expanduser().resolve()
    source_dir = dataset_root / args.episode_subdir
    requested = set(args.episode or [])

    records = []
    for episode_dir in list_episode_dirs(source_dir):
        episode_index = int(episode_dir.name[len("episode") :])
        if requested and episode_index not in requested:
            continue
        try:
            states = aligned_states_for_episode(episode_dir, args.gripper_source)
            summary = summarize_states(states)
            records.append(
                {
                    "episode": episode_dir.name,
                    "frames": int(len(states)),
                    "gripper_source": args.gripper_source,
                    "summary": summary,
                }
            )
            print_episode_summary(episode_dir.name, summary, args.compact)
        except Exception as exc:
            print(f"[skip] {episode_dir.name}: {exc}")

    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "dataset_root": str(dataset_root),
                    "episode_subdir": args.episode_subdir,
                    "gripper_source": args.gripper_source,
                    "episodes": records,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"saved range summary: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
