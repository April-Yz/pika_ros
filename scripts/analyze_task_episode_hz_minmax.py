#!/usr/bin/python3
# 作用: 统计并可视化一个任务下所有 episode 的三相机 Hz 最小值/最大值区间图。

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CAMERA_TOPICS = [
    "/gripper/camera_l/color/image_raw",
    "/gripper/camera_r/color/image_raw",
    "/camera/color/image_raw",
]

CAMERA_LABELS = {
    "/gripper/camera_l/color/image_raw": "gripper_l_color",
    "/gripper/camera_r/color/image_raw": "gripper_r_color",
    "/camera/color/image_raw": "d435_color",
}

CAMERA_COLORS = {
    "/gripper/camera_l/color/image_raw": "#e4572e",
    "/gripper/camera_r/color/image_raw": "#17bebb",
    "/camera/color/image_raw": "#3d5a80",
}


def canonical_topic_name(topic: str) -> str:
    prefix = "/buffered_capture"
    if topic.startswith(prefix + "/"):
        return topic[len(prefix) :]
    return topic


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Visualize per-episode min/max Hz (with filled bands) for 3 camera topics "
            "under a task dataset."
        )
    )
    parser.add_argument(
        "episodes",
        nargs="*",
        type=int,
        help="Optional episode indices, e.g. 3 5 8. If omitted, all numeric episodes are processed.",
    )
    parser.add_argument("--dataset-dir", default=None, help="Dataset root. Overrides --task-name/--dataset-root.")
    parser.add_argument(
        "--dataset-root",
        default=str(Path.home() / "agilex"),
        help="Dataset parent root used together with --task-name.",
    )
    parser.add_argument("--task-name", default="data", help="Task subdirectory under --dataset-root.")
    parser.add_argument(
        "--status-log-name",
        default=None,
        help="Optional status log file name. Auto-detects buffered log if omitted.",
    )
    parser.add_argument(
        "--output-svg",
        default=None,
        help="Output SVG path. Default: <dataset_dir>/episode_hz_minmax.svg",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip episodes missing timing/log matches instead of failing the whole run.",
    )
    return parser.parse_args()


def resolve_dataset_dir(args) -> Path:
    if args.dataset_dir:
        return Path(args.dataset_dir).expanduser()
    return Path(args.dataset_root).expanduser() / args.task_name


def resolve_status_log(dataset_dir: Path, name: Optional[str] = None) -> Path:
    if name:
        return dataset_dir / name
    buffered = dataset_dir / "capture_status_hz_buffered_10hz.log"
    if buffered.exists():
        return buffered
    return dataset_dir / "capture_status_hz.log"


def episode_sort_key(path: Path):
    suffix = path.name[len("episode") :]
    return (0, int(suffix)) if suffix.isdigit() else (1, path.name)


def find_episode_dirs(dataset_dir: Path) -> List[Path]:
    episodes = [
        p
        for p in dataset_dir.iterdir()
        if p.is_dir() and p.name.startswith("episode")
    ]
    return sorted(episodes, key=episode_sort_key)


def parse_capture_window(timing_path: Path) -> Tuple[Optional[float], Optional[float], dt.datetime, dt.datetime]:
    start = None
    end = None
    start_wall = None
    end_wall = None

    for line in timing_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            wall_time = dt.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            continue
        try:
            ros_time = float(parts[1])
        except ValueError:
            ros_time = None

        event = parts[2]
        if event == "capture_object_created":
            start = ros_time
            start_wall = wall_time
        elif event == "capture_shutdown_begin":
            end = ros_time
            end_wall = wall_time

    if start_wall is None or end_wall is None:
        raise RuntimeError(f"Could not parse capture window from {timing_path}")

    return start, end, start_wall, end_wall


def parse_status_log(log_path: Path) -> List[dict]:
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            obj["ros_time"] = float(obj["ros_time"])
            obj["wall_dt"] = dt.datetime.fromisoformat(obj["wall_time"])
        except Exception:
            continue
        entries.append(obj)
    return entries


def filter_records_for_window(
    entries: List[dict],
    start: Optional[float],
    end: Optional[float],
    start_wall: dt.datetime,
    end_wall: dt.datetime,
) -> List[dict]:
    records = []
    wall_margin = dt.timedelta(seconds=1.0)
    start_naive = start_wall.replace(tzinfo=None)
    end_naive = end_wall.replace(tzinfo=None)
    padded_start = None if start is None else start - 1.0
    padded_end = None if end is None else end + 1.0

    for obj in entries:
        ros_time = obj["ros_time"]
        wall_time = obj["wall_dt"]

        matched = False
        if start_naive - wall_margin <= wall_time <= end_naive + wall_margin:
            matched = True
        elif padded_start is not None and padded_end is not None and padded_start <= ros_time <= padded_end:
            matched = True

        if matched:
            records.append(obj)

    return records


def summarize_episode_minmax(records: List[dict]) -> Dict[str, Dict[str, float]]:
    values: Dict[str, List[float]] = {topic: [] for topic in CAMERA_TOPICS}

    for obj in records:
        topics = obj.get("topics", [])
        freqs = obj.get("frequencies", [])
        for topic, freq in zip(topics, freqs):
            canonical_topic = canonical_topic_name(topic)
            if canonical_topic not in values:
                continue
            f = float(freq)
            if math.isfinite(f):
                values[canonical_topic].append(f)

    summary: Dict[str, Dict[str, float]] = {}
    for topic in CAMERA_TOPICS:
        topic_vals = values[topic]
        if topic_vals:
            summary[topic] = {
                "min": min(topic_vals),
                "max": max(topic_vals),
            }
        else:
            summary[topic] = {
                "min": math.nan,
                "max": math.nan,
            }

    return summary


def build_svg(
    episode_ids: List[int],
    episode_stats: Dict[int, Dict[str, Dict[str, float]]],
    output_svg: Path,
):
    left = 90
    right = 350
    top = 70
    bottom = 110
    width = max(1200, left + right + 60 * max(1, len(episode_ids)))
    height = 700

    plot_w = width - left - right
    plot_h = height - top - bottom

    y_min = 0.0
    y_max = 15.0

    x_min = min(episode_ids)
    x_max = max(episode_ids)
    x_span = max(1.0, float(x_max - x_min))

    def x_px(ep: float) -> float:
        return left + ((ep - x_min) / x_span) * plot_w

    def y_px(hz: float) -> float:
        clipped = min(max(hz, y_min), y_max)
        return top + plot_h - ((clipped - y_min) / (y_max - y_min)) * plot_h

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect width="100%" height="100%" fill="#fbfbf8"/>')
    svg.append(
        f'<text x="{left}" y="35" font-size="24" font-family="monospace" fill="#222">Episode Camera Hz Min/Max (Y: 0-15 Hz)</text>'
    )

    for tick in [0, 3, 6, 9, 12, 15]:
        y = y_px(float(tick))
        svg.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#dadada" stroke-width="1" stroke-dasharray="4,4"/>'
        )
        svg.append(
            f'<text x="{left - 10}" y="{y + 5:.2f}" text-anchor="end" font-size="14" font-family="monospace" fill="#333">{tick}</text>'
        )

    tick_step = max(1, int(math.ceil(len(episode_ids) / 16.0)))
    shown_eps = episode_ids[::tick_step]
    if episode_ids[-1] not in shown_eps:
        shown_eps.append(episode_ids[-1])

    for ep in shown_eps:
        x = x_px(float(ep))
        svg.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_h}" stroke="#e4e4e4" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{x:.2f}" y="{top + plot_h + 26}" text-anchor="middle" font-size="13" font-family="monospace" fill="#333">{ep}</text>'
        )

    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222" stroke-width="2"/>')
    svg.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222" stroke-width="2"/>'
    )
    svg.append(
        f'<text x="{left - 60}" y="{top + plot_h / 2}" transform="rotate(-90 {left - 60} {top + plot_h / 2})" text-anchor="middle" font-size="18" font-family="monospace" fill="#222">Hz (0-15)</text>'
    )
    svg.append(
        f'<text x="{left + plot_w / 2}" y="{height - 30}" text-anchor="middle" font-size="18" font-family="monospace" fill="#222">Episode Index</text>'
    )

    for topic in CAMERA_TOPICS:
        color = CAMERA_COLORS[topic]
        min_points = []
        max_points = []

        for ep in episode_ids:
            min_hz = episode_stats[ep][topic]["min"]
            max_hz = episode_stats[ep][topic]["max"]
            if not (math.isfinite(min_hz) and math.isfinite(max_hz)):
                continue
            min_points.append((x_px(float(ep)), y_px(min_hz)))
            max_points.append((x_px(float(ep)), y_px(max_hz)))

        if not min_points or not max_points:
            continue

        band_poly = min_points + list(reversed(max_points))
        band_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in band_poly)
        min_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in min_points)
        max_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in max_points)

        svg.append(
            f'<polygon points="{band_str}" fill="{color}" fill-opacity="0.18" stroke="none"/>'
        )
        svg.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{min_str}"/>'
        )
        svg.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{max_str}"/>'
        )

    legend_x = left + plot_w + 24
    legend_y = top + 24
    svg.append(
        f'<text x="{legend_x}" y="{legend_y}" font-size="18" font-family="monospace" fill="#222">3 Cameras (min/max + filled range)</text>'
    )

    row_y = legend_y + 28
    for topic in CAMERA_TOPICS:
        color = CAMERA_COLORS[topic]
        label = CAMERA_LABELS[topic]
        svg.append(
            f'<rect x="{legend_x}" y="{row_y - 12}" width="22" height="12" fill="{color}" fill-opacity="0.18"/>'
        )
        svg.append(
            f'<line x1="{legend_x}" y1="{row_y - 6}" x2="{legend_x + 22}" y2="{row_y - 6}" stroke="{color}" stroke-width="2.5"/>'
        )
        svg.append(
            f'<text x="{legend_x + 30}" y="{row_y - 1}" font-size="14" font-family="monospace" fill="#222">{label}</text>'
        )
        row_y += 28

    svg.append('</svg>')
    output_svg.write_text("\n".join(svg), encoding="utf-8")


def main() -> int:
    args = parse_args()

    dataset_dir = resolve_dataset_dir(args)
    if not dataset_dir.is_dir():
        raise SystemExit(f"Dataset directory not found: {dataset_dir}")

    status_log = resolve_status_log(dataset_dir, args.status_log_name)
    if not status_log.exists():
        raise SystemExit(f"Status log not found: {status_log}")

    all_episode_dirs = find_episode_dirs(dataset_dir)
    if not all_episode_dirs:
        raise SystemExit(f"No episode directories found under: {dataset_dir}")

    if args.episodes:
        episode_ids = list(dict.fromkeys(args.episodes))
    else:
        episode_ids = [
            int(ep.name[len("episode") :])
            for ep in all_episode_dirs
            if ep.name[len("episode") :].isdigit()
        ]

    if not episode_ids:
        raise SystemExit("No numeric episodes found. Pass explicit episode IDs if needed.")

    all_entries = parse_status_log(status_log)
    if not all_entries:
        raise SystemExit(f"No valid status log entries found in: {status_log}")

    episode_stats: Dict[int, Dict[str, Dict[str, float]]] = {}
    skipped = []

    for ep_id in episode_ids:
        ep_dir = dataset_dir / f"episode{ep_id}"
        timing_path = ep_dir / "capture_timing.log"

        try:
            start, end, start_wall, end_wall = parse_capture_window(timing_path)
            records = filter_records_for_window(all_entries, start, end, start_wall, end_wall)
            if not records:
                raise RuntimeError("No capture_status records matched this episode window")
            episode_stats[ep_id] = summarize_episode_minmax(records)
        except Exception as exc:
            msg = f"episode{ep_id} skipped: {exc}"
            if args.skip_missing:
                print(f"[skip] {msg}")
                skipped.append(ep_id)
                continue
            raise SystemExit(msg)

    if not episode_stats:
        raise SystemExit("No episode statistics collected.")

    used_episode_ids = sorted(episode_stats.keys())

    output_svg = (
        Path(args.output_svg).expanduser()
        if args.output_svg
        else dataset_dir / "episode_hz_minmax.svg"
    )
    output_svg.parent.mkdir(parents=True, exist_ok=True)

    build_svg(used_episode_ids, episode_stats, output_svg)

    print(f"Saved plot to: {output_svg}")
    print(f"Episodes visualized: {len(used_episode_ids)}")
    if skipped:
        print(f"Episodes skipped: {len(skipped)}")

    for ep in used_episode_ids:
        print(f"\nEpisode {ep}")
        for topic in CAMERA_TOPICS:
            label = CAMERA_LABELS[topic]
            mn = episode_stats[ep][topic]["min"]
            mx = episode_stats[ep][topic]["max"]
            if math.isfinite(mn) and math.isfinite(mx):
                print(f"- {label}: min={mn:.3f} Hz, max={mx:.3f} Hz")
            else:
                print(f"- {label}: no finite data")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
