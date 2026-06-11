#!/usr/bin/env python3
"""
Curate raw teleop episode directories after overview videos are rendered.

Step 2.1 auto-split:
  Move structurally valid and sufficiently frequent episodes from `unprocessed/`
  into `good/`.
  Move missing-view / low-hz / missing-video episodes into `bad/system/`.

Step 2.2 manual-review:
  Play `good/episode*/camera_overview.mp4` in order and let the operator
  keep, medium-mark, or reject episodes with keyboard controls.
  Manual rejects are moved into `bad/manual/`.

Examples:
  /usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py auto-split \
    --task-name pnp_bread

  /usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py manual-review \
    --task-name pnp_bread
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import cv2


RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
HEAD_CAM_DIRNAME = "myD435"
TARGET_RGB_HZ = 10.0
MIN_RGB_HZ = 8.0


@dataclass(frozen=True)
class EpisodeCheck:
    ok: bool
    level: str
    reason: str
    detail: str


def print_colored(level: str, message: str) -> None:
    if level == "ERROR":
        print(f"{RED}{message}{RESET}")
    elif level == "WARNING":
        print(f"{YELLOW}{message}{RESET}")
    elif level == "MEDIUM":
        print(f"{BLUE}{message}{RESET}")
    else:
        print(message)


def episode_sort_key(path: Path):
    suffix = path.name[len("episode") :]
    return (0, int(suffix)) if suffix.isdigit() else (1, path.name)


def resolve_dataset_dir(args) -> Path:
    if args.dataset_dir:
        return Path(args.dataset_dir).expanduser().resolve()
    return (Path(args.dataset_root).expanduser() / args.task_name).resolve()


def list_episode_dirs(root: Path) -> List[Path]:
    return sorted(
        [path for path in root.iterdir() if path.is_dir() and path.name.startswith("episode")],
        key=episode_sort_key,
    )


def count_files(path: Path, suffix: str) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.is_file() and item.suffix.lower() == suffix)


def parse_episode_rgb_hz(episode_dir: Path) -> Optional[Dict[str, float]]:
    statistic_path = episode_dir / "statistic.txt"
    if not statistic_path.exists():
        return None

    keys = [
        "camera/color/pikaGripperDepthCamera_l",
        "camera/color/pikaGripperDepthCamera_r",
        f"camera/color/{HEAD_CAM_DIRNAME}",
    ]
    hz_map: Dict[str, float] = {}
    with statistic_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            parts = raw_line.strip().split()
            if len(parts) < 3 or parts[0] not in keys:
                continue
            try:
                hz_map[parts[0]] = float(parts[-1])
            except ValueError:
                continue
    return hz_map if len(hz_map) == len(keys) else None


def check_episode(episode_dir: Path, gripper_source: str, min_rgb_hz: float, video_name: str) -> EpisodeCheck:
    required_counts = {
        "cam_left_wrist": count_files(episode_dir / "camera" / "color" / "pikaGripperDepthCamera_l", ".jpg"),
        "cam_right_wrist": count_files(episode_dir / "camera" / "color" / "pikaGripperDepthCamera_r", ".jpg"),
        "cam_high": count_files(episode_dir / "camera" / "color" / HEAD_CAM_DIRNAME, ".jpg"),
        "state_left_pose": count_files(episode_dir / "arm" / "endPose" / "puppetLeft", ".json"),
        "state_right_pose": count_files(episode_dir / "arm" / "endPose" / "puppetRight", ".json"),
    }
    if gripper_source == "sensor":
        required_counts["left_gripper_sensor"] = count_files(episode_dir / "gripper" / "encoder" / "pikaSensor_l", ".json")
        required_counts["right_gripper_sensor"] = count_files(episode_dir / "gripper" / "encoder" / "pikaSensor_r", ".json")
    else:
        required_counts["left_gripper_robot"] = count_files(episode_dir / "gripper" / "encoder" / "pikaGripper_l", ".json")
        required_counts["right_gripper_robot"] = count_files(episode_dir / "gripper" / "encoder" / "pikaGripper_r", ".json")

    missing = [name for name, count in required_counts.items() if count <= 1]
    if missing:
        detail = ", ".join(f"{name}={required_counts[name]}" for name in missing)
        return EpisodeCheck(False, "ERROR", "missing_required_data", detail)

    video_path = episode_dir / video_name
    if not video_path.is_file() or video_path.stat().st_size <= 0:
        return EpisodeCheck(False, "ERROR", "missing_overview_video", str(video_path))

    hz_map = parse_episode_rgb_hz(episode_dir)
    if hz_map is None:
        return EpisodeCheck(False, "ERROR", "missing_rgb_hz_stat", "statistic.txt missing or incomplete")
    min_key = min(hz_map, key=hz_map.get)
    min_hz = hz_map[min_key]
    detail = ", ".join(f"{key}={value:.3f}" for key, value in hz_map.items())
    if min_hz < min_rgb_hz:
        return EpisodeCheck(False, "ERROR", "rgb_hz_too_low", f"min_rgb_hz={min_hz:.3f} on {min_key}; {detail}")
    if min_hz < TARGET_RGB_HZ:
        return EpisodeCheck(True, "WARNING", "rgb_hz_below_target", f"min_rgb_hz={min_hz:.3f} on {min_key}; {detail}")
    return EpisodeCheck(True, "INFO", "ok", detail)


def write_log(log_path: Path, record: Dict[str, object]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_review_overlay(
    episode_name: str,
    index: int,
    total: int,
    reviewed: int,
    kept_good: int,
    moved_medium: int,
    moved_bad: int,
    speed: float,
) -> List[str]:
    return [
        f"{episode_name} [{index + 1}/{total}]",
        f"reviewed={reviewed} remaining={max(total - reviewed, 0)}",
        f"good={kept_good} medium={moved_medium} bad={moved_bad}",
        f"speed={speed:.2f}x",
        "g good | m medium | b bad | n next | p prev | r replay | a slower | d faster | space pause | q quit",
    ]


def move_episode(src: Path, dst_root: Path, overwrite_existing: bool) -> Path:
    dst_root.mkdir(parents=True, exist_ok=True)
    dst = dst_root / src.name
    if dst.exists():
        if not overwrite_existing:
            raise FileExistsError(f"Destination already exists: {dst}")
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))
    return dst


def auto_split(args) -> int:
    dataset_dir = resolve_dataset_dir(args)
    incoming_dir = dataset_dir / args.incoming_name
    good_dir = dataset_dir / args.good_name
    bad_dir = dataset_dir / args.bad_name / args.system_bad_name
    log_path = dataset_dir / "curation_log.jsonl"

    episodes = list_episode_dirs(incoming_dir)
    if not episodes:
        raise SystemExit(f"No episode directories found under {incoming_dir}")

    good_count = 0
    bad_count = 0
    for episode_dir in episodes:
        check = check_episode(episode_dir, args.gripper_source, args.min_rgb_hz, args.video_name)
        dst_root = good_dir if check.ok else bad_dir
        try:
            dst = move_episode(episode_dir, dst_root, args.overwrite_existing)
        except FileExistsError as exc:
            print_colored("ERROR", f"[skip] {episode_dir.name}: {exc}")
            write_log(log_path, {"episode": episode_dir.name, "action": "skip", "level": "ERROR", "reason": "destination_exists", "detail": str(exc)})
            continue

        action = "move_good" if check.ok else "move_bad"
        good_count += 1 if check.ok else 0
        bad_count += 0 if check.ok else 1
        print_colored(check.level, f"[{action}] {episode_dir.name}: {check.reason}: {check.detail}")
        write_log(
            log_path,
            {
                "episode": episode_dir.name,
                "action": action,
                "level": check.level,
                "reason": check.reason,
                "detail": check.detail,
                "destination": str(dst),
            },
        )

    print(f"auto split done: good={good_count}, bad={bad_count}, log={log_path}")
    return 0


def play_video(video_path: Path, window_name: str, fps_fallback: float, overlay_lines: List[str]) -> str:
    speed_levels = [0.25, 0.5, 1.0, 2.0, 4.0]
    speed_index = speed_levels.index(1.0)
    while True:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return "bad"
        fps = cap.get(cv2.CAP_PROP_FPS)
        decision = None
        paused = False
        while True:
            current_speed = speed_levels[speed_index]
            delay = max(1, int(1000.0 / ((fps if fps > 1e-6 else fps_fallback) * current_speed)))
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    paused = True
                    continue
                y = 32
                for line in overlay_lines[:-2]:
                    cv2.putText(
                        frame,
                        line,
                        (16, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    y += 30
                cv2.putText(
                    frame,
                    f"speed={current_speed:.2f}x",
                    (16, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                y += 30
                cv2.putText(
                    frame,
                    overlay_lines[-1],
                    (16, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.62,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, frame)
            key = cv2.waitKey(0 if paused else delay) & 0xFF
            if key in (ord(" "),):
                paused = not paused
            elif key in (ord("r"),):
                decision = "replay"
                break
            elif key == ord("a"):
                speed_index = max(0, speed_index - 1)
            elif key == ord("d"):
                speed_index = min(len(speed_levels) - 1, speed_index + 1)
            elif key in (ord("g"), ord("n")):
                decision = "good"
                break
            elif key == ord("m"):
                decision = "medium"
                break
            elif key == ord("b"):
                decision = "bad"
                break
            elif key == ord("p"):
                decision = "prev"
                break
            elif key == ord("q"):
                decision = "quit"
                break
        cap.release()
        if decision != "replay":
            return decision or "good"


def manual_review(args) -> int:
    dataset_dir = resolve_dataset_dir(args)
    good_dir = dataset_dir / args.good_name
    medium_dir = dataset_dir / args.medium_name
    bad_dir = dataset_dir / args.bad_name / args.manual_bad_name
    log_path = dataset_dir / "manual_curation_log.jsonl"
    episodes = list_episode_dirs(good_dir)
    if not episodes:
        raise SystemExit(f"No episode directories found under {good_dir}")

    total = len(episodes)
    reviewed = 0
    kept_good = 0
    moved_medium = 0
    moved_bad = 0
    index = 0
    window_name = f"review {dataset_dir.name}"
    while 0 <= index < len(episodes):
        episode_dir = episodes[index]
        if not episode_dir.exists():
            episodes = list_episode_dirs(good_dir)
            index = min(index, len(episodes) - 1)
            continue

        video_path = episode_dir / args.video_name
        print(f"[review] {episode_dir.name}: {video_path}")
        overlay_lines = build_review_overlay(
            episode_dir.name,
            index,
            total,
            reviewed,
            kept_good,
            moved_medium,
            moved_bad,
            1.0,
        )
        decision = play_video(video_path, window_name, args.fps_fallback, overlay_lines)
        if decision == "quit":
            break
        if decision == "prev":
            index = max(0, index - 1)
            continue
        if decision == "bad":
            dst = move_episode(episode_dir, bad_dir, args.overwrite_existing)
            print_colored("ERROR", f"[manual_bad] {episode_dir.name} -> {dst}")
            write_log(log_path, {"episode": episode_dir.name, "action": "manual_bad", "destination": str(dst)})
            moved_bad += 1
            reviewed += 1
            episodes = list_episode_dirs(good_dir)
            index = min(index, len(episodes))
            continue
        if decision == "medium":
            dst = move_episode(episode_dir, medium_dir, args.overwrite_existing)
            print_colored("MEDIUM", f"[manual_medium] {episode_dir.name} -> {dst}")
            write_log(log_path, {"episode": episode_dir.name, "action": "manual_medium", "destination": str(dst)})
            moved_medium += 1
            reviewed += 1
            episodes = list_episode_dirs(good_dir)
            index = min(index, len(episodes))
            continue

        write_log(log_path, {"episode": episode_dir.name, "action": "manual_good", "path": str(episode_dir)})
        print(f"[manual_good] {episode_dir.name}")
        kept_good += 1
        reviewed += 1
        index += 1

    cv2.destroyAllWindows()
    print(f"manual review log: {log_path}")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-split and manually review teleop raw episodes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub):
        sub.add_argument("--dataset-dir", default=None)
        sub.add_argument("--dataset-root", default=str(Path.home() / "agilex"))
        sub.add_argument("--task-name", default="data")
        sub.add_argument("--incoming-name", default="unprocessed")
        sub.add_argument("--good-name", default="good")
        sub.add_argument("--medium-name", default="medium")
        sub.add_argument("--bad-name", default="bad")
        sub.add_argument("--system-bad-name", default="system")
        sub.add_argument("--manual-bad-name", default="manual")
        sub.add_argument("--video-name", default="camera_overview.mp4")
        sub.add_argument("--overwrite-existing", action="store_true")

    auto = subparsers.add_parser("auto-split", help="Move root episodes into good/bad folders.")
    add_common(auto)
    auto.add_argument("--gripper-source", choices=["robot", "sensor"], default="robot")
    auto.add_argument("--min-rgb-hz", type=float, default=MIN_RGB_HZ)

    review = subparsers.add_parser("manual-review", help="Review videos in the good folder.")
    add_common(review)
    review.add_argument("--fps-fallback", type=float, default=20.0)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "auto-split":
        return auto_split(args)
    if args.command == "manual-review":
        return manual_review(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
