#!/usr/bin/env python3
"""
Downsample raw teleop episodes by removing near-static frames.

The script reads raw `episode*` directories, aligns modalities by head camera
timestamps, keeps the first and last frame, and keeps intermediate frames only
when the summed absolute 7D end-effector change since the last kept frame
exceeds `--motion-threshold`.

For dual-arm data, the left and right motion-state changes are computed
separately and a frame is kept if either arm exceeds the threshold.

Motion-state definition:
- `--gripper-source robot`: per arm uses 7D
  `x, y, z, roll, pitch, yaw, robot_gripper_distance`
- `--gripper-source sensor`: per arm uses 8D
  `x, y, z, roll, pitch, yaw, robot_gripper_distance, sensor_gripper_distance`

Rotation is not converted into linear distance. `roll`, `pitch`, and `yaw` are
read directly from the raw JSON pose files and used as radian deltas in the
same summed threshold as position and gripper distance.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np


HEAD_CAM_DIRNAME = "myD435"


@dataclass(frozen=True)
class EpisodePaths:
    episode_dir: Path
    left_rgb: Path
    right_rgb: Path
    head_rgb: Path
    left_pose: Path
    right_pose: Path
    robot_left_gripper: Path
    robot_right_gripper: Path
    sensor_left_gripper: Path
    sensor_right_gripper: Path


def episode_sort_key(path: Path):
    suffix = path.name[len("episode") :]
    return (0, int(suffix)) if suffix.isdigit() else (1, path.name)


def list_episode_dirs(root: Path) -> List[Path]:
    return sorted(
        [path for path in root.iterdir() if path.is_dir() and path.name.startswith("episode")],
        key=episode_sort_key,
    )


def timestamp(path: Path) -> float:
    return float(path.stem)


def list_files(path: Path, suffix: str) -> List[Path]:
    if not path.is_dir():
        return []
    return sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() == suffix], key=timestamp)


def nearest(files: Sequence[Path], target: float) -> Path:
    if not files:
        raise ValueError("nearest received empty files")
    return min(files, key=lambda path: abs(timestamp(path) - target))


def load_pose(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return np.array([data["x"], data["y"], data["z"], data["roll"], data["pitch"], data["yaw"]], dtype=np.float32)


def load_gripper(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return np.array([data["distance"]], dtype=np.float32)


def build_paths(episode_dir: Path) -> EpisodePaths:
    return EpisodePaths(
        episode_dir=episode_dir,
        left_rgb=episode_dir / "camera" / "color" / "pikaGripperDepthCamera_l",
        right_rgb=episode_dir / "camera" / "color" / "pikaGripperDepthCamera_r",
        head_rgb=episode_dir / "camera" / "color" / HEAD_CAM_DIRNAME,
        left_pose=episode_dir / "arm" / "endPose" / "puppetLeft",
        right_pose=episode_dir / "arm" / "endPose" / "puppetRight",
        robot_left_gripper=episode_dir / "gripper" / "encoder" / "pikaGripper_l",
        robot_right_gripper=episode_dir / "gripper" / "encoder" / "pikaGripper_r",
        sensor_left_gripper=episode_dir / "gripper" / "encoder" / "pikaSensor_l",
        sensor_right_gripper=episode_dir / "gripper" / "encoder" / "pikaSensor_r",
    )


def motion_gripper_dirs(paths: EpisodePaths, gripper_source: str) -> Tuple[List[Path], List[Path]]:
    if gripper_source == "sensor":
        return (
            [paths.robot_left_gripper, paths.sensor_left_gripper],
            [paths.robot_right_gripper, paths.sensor_right_gripper],
        )
    return ([paths.robot_left_gripper], [paths.robot_right_gripper])

def aligned_motion_state_at(
    ts: float,
    left_pose_files: Sequence[Path],
    right_pose_files: Sequence[Path],
    left_gripper_file_groups: Sequence[Sequence[Path]],
    right_gripper_file_groups: Sequence[Sequence[Path]],
) -> np.ndarray:
    left_parts = [load_pose(nearest(left_pose_files, ts))]
    for files in left_gripper_file_groups:
        left_parts.append(load_gripper(nearest(files, ts)))
    right_parts = [load_pose(nearest(right_pose_files, ts))]
    for files in right_gripper_file_groups:
        right_parts.append(load_gripper(nearest(files, ts)))
    left = np.concatenate(left_parts)
    right = np.concatenate(right_parts)
    return np.concatenate([left, right]).astype(np.float32)


def keep_indices(states: np.ndarray, threshold: float) -> List[int]:
    if len(states) <= 2:
        return list(range(len(states)))
    arm_dim = states.shape[1] // 2
    kept = [0]
    last_kept = 0
    for idx in range(1, len(states) - 1):
        left_delta = float(np.abs(states[idx, :arm_dim] - states[last_kept, :arm_dim]).sum())
        right_delta = float(np.abs(states[idx, arm_dim:] - states[last_kept, arm_dim:]).sum())
        if max(left_delta, right_delta) >= threshold:
            kept.append(idx)
            last_kept = idx
    if kept[-1] != len(states) - 1:
        kept.append(len(states) - 1)
    return kept


def copy_nearest_files(dst_episode: Path, mappings: Iterable[Tuple[Path, str, Sequence[Path], str]], timestamps: Sequence[float]) -> None:
    for _src_root, rel_dir, files, suffix in mappings:
        dst_dir = dst_episode / rel_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        copied = set()
        for ts in timestamps:
            src = nearest(files, ts)
            if src in copied:
                continue
            copied.add(src)
            shutil.copy2(src, dst_dir / src.name)


def copy_metadata(src_episode: Path, dst_episode: Path) -> None:
    for name in ["instructions.json", "statistic.txt", "capture_timing.log", "hz_summary.svg"]:
        src = src_episode / name
        if src.exists():
            shutil.copy2(src, dst_episode / name)
    for config in src_episode.glob("camera/*/*/config.json"):
        rel = config.relative_to(src_episode)
        dst = dst_episode / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config, dst)


def render_trimmed_overview(dst_episode: Path) -> None:
    script = Path(__file__).resolve().parent / "render_episode_camera_video.py"
    output = dst_episode / "camera_overview.mp4"
    cmd = [
        sys.executable,
        str(script),
        str(dst_episode),
        "--dataset-dir",
        str(dst_episode.parent),
        "--output",
        str(output),
        "--overwrite",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def trim_episode(episode_dir: Path, output_dir: Path, threshold: float, gripper_source: str, overwrite: bool) -> Dict[str, object]:
    paths = build_paths(episode_dir)
    head_files = list_files(paths.head_rgb, ".jpg")
    left_rgb_files = list_files(paths.left_rgb, ".jpg")
    right_rgb_files = list_files(paths.right_rgb, ".jpg")
    left_pose_files = list_files(paths.left_pose, ".json")
    right_pose_files = list_files(paths.right_pose, ".json")
    left_gripper_dirs, right_gripper_dirs = motion_gripper_dirs(paths, gripper_source)
    left_gripper_file_groups = [list_files(path, ".json") for path in left_gripper_dirs]
    right_gripper_file_groups = [list_files(path, ".json") for path in right_gripper_dirs]

    required = [
        head_files,
        left_rgb_files,
        right_rgb_files,
        left_pose_files,
        right_pose_files,
        *left_gripper_file_groups,
        *right_gripper_file_groups,
    ]
    if any(len(files) < 2 for files in required):
        return {"episode": episode_dir.name, "status": "skipped", "reason": "missing_required_files"}

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
    kept = keep_indices(states, threshold)
    kept_ts = [timeline[idx] for idx in kept]

    dst_episode = output_dir / episode_dir.name
    if dst_episode.exists():
        if not overwrite:
            return {"episode": episode_dir.name, "status": "skipped", "reason": "destination_exists", "destination": str(dst_episode)}
        shutil.rmtree(dst_episode)
    dst_episode.mkdir(parents=True, exist_ok=True)

    copy_nearest_files(
        dst_episode,
        [
            (paths.head_rgb, "camera/color/myD435", head_files, ".jpg"),
            (paths.left_rgb, "camera/color/pikaGripperDepthCamera_l", left_rgb_files, ".jpg"),
            (paths.right_rgb, "camera/color/pikaGripperDepthCamera_r", right_rgb_files, ".jpg"),
            (paths.left_pose, "arm/endPose/puppetLeft", left_pose_files, ".json"),
            (paths.right_pose, "arm/endPose/puppetRight", right_pose_files, ".json"),
            (paths.robot_left_gripper, "gripper/encoder/pikaGripper_l", list_files(paths.robot_left_gripper, ".json"), ".json"),
            (paths.robot_right_gripper, "gripper/encoder/pikaGripper_r", list_files(paths.robot_right_gripper, ".json"), ".json"),
            (paths.sensor_left_gripper, "gripper/encoder/pikaSensor_l", list_files(paths.sensor_left_gripper, ".json"), ".json"),
            (paths.sensor_right_gripper, "gripper/encoder/pikaSensor_r", list_files(paths.sensor_right_gripper, ".json"), ".json"),
        ],
        kept_ts,
    )
    copy_metadata(episode_dir, dst_episode)
    render_trimmed_overview(dst_episode)

    original = len(timeline)
    kept_count = len(kept)
    return {
        "episode": episode_dir.name,
        "status": "ok",
        "original_frames": original,
        "kept_frames": kept_count,
        "kept_percent": kept_count * 100.0 / original if original else 0.0,
        "removed_frames": original - kept_count,
        "motion_threshold": threshold,
        "destination": str(dst_episode),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Trim near-static frames from raw good teleop episodes.")
    parser.add_argument("input_dir", help="Directory containing episode* folders, e.g. ~/agilex/pnp_bread/good")
    parser.add_argument("--output-dir", required=True, help="Destination directory for trimmed raw episodes")
    parser.add_argument(
        "--motion-threshold",
        type=float,
        default=0.01,
        help="Threshold on summed absolute 7D motion per arm. Default: 0.01",
    )
    parser.add_argument("--gripper-source", choices=["robot", "sensor"], default="robot")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "static_trim_report.json"

    records = []
    for episode_dir in list_episode_dirs(input_dir):
        record = trim_episode(episode_dir, output_dir, args.motion_threshold, args.gripper_source, args.overwrite)
        records.append(record)
        if record.get("status") == "ok":
            print(
                f"[ok] {record['episode']}: kept {record['kept_frames']}/{record['original_frames']} "
                f"({record['kept_percent']:.2f}%)"
            )
        else:
            print(f"[skip] {record['episode']}: {record.get('reason')}")

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "motion_threshold": args.motion_threshold,
        "gripper_source": args.gripper_source,
        "episodes": records,
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"saved trim report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
