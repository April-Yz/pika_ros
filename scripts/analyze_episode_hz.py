#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

TOPICS = [
    "/gripper/camera_l/color/image_raw",
    "/gripper/camera_r/color/image_raw",
    "/gripper/camera_l/aligned_depth_to_color/image_raw",
    "/gripper/camera_r/aligned_depth_to_color/image_raw",
    "/camera/color/image_raw",
    "/gripper/camera_fisheye_r/color/image_raw",
    "/gripper/camera_fisheye_l/color/image_raw",
]

TOPIC_LABELS = {
    "/gripper/camera_l/color/image_raw": "gripper_l_color",
    "/gripper/camera_r/color/image_raw": "gripper_r_color",
    "/gripper/camera_l/aligned_depth_to_color/image_raw": "gripper_l_depth",
    "/gripper/camera_r/aligned_depth_to_color/image_raw": "gripper_r_depth",
    "/camera/color/image_raw": "d435_color",
    "/gripper/camera_fisheye_r/color/image_raw": "fisheye_r",
    "/gripper/camera_fisheye_l/color/image_raw": "fisheye_l",
}

TOPIC_COLORS = {
    "/gripper/camera_l/color/image_raw": "#d1495b",
    "/gripper/camera_r/color/image_raw": "#00798c",
    "/gripper/camera_l/aligned_depth_to_color/image_raw": "#edae49",
    "/gripper/camera_r/aligned_depth_to_color/image_raw": "#30638e",
    "/camera/color/image_raw": "#66a182",
    "/gripper/camera_fisheye_r/color/image_raw": "#8e5572",
    "/gripper/camera_fisheye_l/color/image_raw": "#5c6b73",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize and visualize capture_status_hz.log for one episode."
    )
    parser.add_argument("episode", type=int, help="Episode index, e.g. 28")
    parser.add_argument("--dataset-dir", default=str(Path.home() / "agilex" / "data"))
    parser.add_argument(
        "--output-svg",
        default=None,
        help="Optional output SVG path. Defaults to episodeN/hz_summary.svg",
    )
    return parser.parse_args()


def parse_capture_window(timing_path: Path) -> Tuple[float, float, dt.datetime, dt.datetime]:
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


def load_records(log_path: Path, start: float, end: float, start_wall: dt.datetime, end_wall: dt.datetime) -> List[dict]:
    records = []
    padded_start = None if start is None else start - 3.0
    padded_end = None if end is None else end + 3.0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        ros_time = float(obj["ros_time"])
        matched = False
        if padded_start is not None and padded_end is not None and padded_start <= ros_time <= padded_end:
            matched = True
        else:
            wall_time = dt.datetime.fromisoformat(obj["wall_time"])
            start_naive = start_wall.replace(tzinfo=None)
            end_naive = end_wall.replace(tzinfo=None)
            if start_naive - dt.timedelta(seconds=3) <= wall_time <= end_naive + dt.timedelta(seconds=3):
                matched = True
        if matched:
            records.append(obj)
    if not records:
        raise RuntimeError(f"No capture_status records found in {log_path} for selected window")
    return records


def summarize(records: List[dict]) -> Dict[str, dict]:
    topic_data: Dict[str, List[Tuple[float, float]]] = {topic: [] for topic in TOPICS}
    base_time = float(records[0]["ros_time"])
    for obj in records:
        rel_time = float(obj["ros_time"]) - base_time
        for topic, freq in zip(obj["topics"], obj["frequencies"]):
            if topic not in topic_data:
                continue
            topic_data[topic].append((rel_time, float(freq)))

    summary = {}
    for topic in TOPICS:
        series = topic_data[topic]
        finite = [v for _, v in series if math.isfinite(v)]
        if finite:
            summary[topic] = {
                "avg": sum(finite) / len(finite),
                "min": min(finite),
                "max": max(finite),
                "series": series,
            }
        else:
            summary[topic] = {"avg": math.nan, "min": math.nan, "max": math.nan, "series": series}
    return summary


def y_transform(freq: float) -> float:
    clipped = max(0.0, min(50.0, freq))
    if clipped <= 15.0:
        return clipped * 2.0
    return 30.0 + (clipped - 15.0) * (20.0 / 35.0)


def build_svg(summary: Dict[str, dict], duration: float, output_path: Path):
    width = 1600
    height = 900
    left = 100
    right = 330
    top = 60
    bottom = 90
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_px(seconds: float) -> float:
        if duration <= 0:
            return left
        return left + (seconds / duration) * plot_w

    def y_px(freq: float) -> float:
        transformed = y_transform(freq)
        return top + plot_h - (transformed / 50.0) * plot_h

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect width="100%" height="100%" fill="#fcfcf8"/>')
    svg.append(f'<text x="{left}" y="30" font-size="24" font-family="monospace" fill="#222">Episode Hz Summary</text>')

    low_band_top = y_px(15)
    svg.append(f'<rect x="{left}" y="{low_band_top}" width="{plot_w}" height="{top + plot_h - low_band_top}" fill="#fff0d8" opacity="0.85"/>')

    tick_values = [0, 5, 10, 15, 20, 30, 40, 50]
    for value in tick_values:
        y = y_px(value)
        dash = "4,4" if value != 15 else "8,4"
        color = "#d0d0d0" if value != 15 else "#c98300"
        svg.append(f'<line x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}" stroke="{color}" stroke-width="1" stroke-dasharray="{dash}"/>')
        svg.append(f'<text x="{left - 12}" y="{y + 5}" text-anchor="end" font-size="14" font-family="monospace" fill="#333">{value}</text>')

    x_ticks = 8
    for idx in range(x_ticks + 1):
        sec = duration * idx / x_ticks if duration > 0 else 0
        x = x_px(sec)
        svg.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + plot_h}" stroke="#e0e0e0" stroke-width="1"/>')
        svg.append(f'<text x="{x}" y="{top + plot_h + 25}" text-anchor="middle" font-size="14" font-family="monospace" fill="#333">{sec:.1f}s</text>')

    svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222" stroke-width="2"/>')
    svg.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222" stroke-width="2"/>')
    svg.append(f'<text x="{left - 70}" y="{top + plot_h / 2}" transform="rotate(-90 {left - 70} {top + plot_h / 2})" text-anchor="middle" font-size="18" font-family="monospace" fill="#222">Frequency (Hz, clipped to 50)</text>')
    svg.append(f'<text x="{left + plot_w / 2}" y="{height - 25}" text-anchor="middle" font-size="18" font-family="monospace" fill="#222">Time Since Capture Start (s)</text>')

    for topic in TOPICS:
        series = summary[topic]["series"]
        color = TOPIC_COLORS[topic]
        points = []
        for rel_time, freq in series:
            if not math.isfinite(freq):
                continue
            points.append(f"{x_px(rel_time):.2f},{y_px(freq):.2f}")
        if points:
            svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{" ".join(points)}"/>')

    legend_x = left + plot_w + 30
    legend_y = top + 20
    svg.append(f'<text x="{legend_x}" y="{legend_y}" font-size="18" font-family="monospace" fill="#222">Summary</text>')
    row_y = legend_y + 24
    for topic in TOPICS:
        color = TOPIC_COLORS[topic]
        label = TOPIC_LABELS[topic]
        avg = summary[topic]["avg"]
        min_v = summary[topic]["min"]
        max_v = summary[topic]["max"]
        svg.append(f'<line x1="{legend_x}" y1="{row_y - 6}" x2="{legend_x + 20}" y2="{row_y - 6}" stroke="{color}" stroke-width="4"/>')
        if math.isfinite(avg):
            text = f"{label}: avg {avg:.3f} min {min_v:.3f} max {max_v:.3f}"
        else:
            text = f"{label}: no finite data"
        svg.append(f'<text x="{legend_x + 28}" y="{row_y}" font-size="13" font-family="monospace" fill="#222">{text}</text>')
        row_y += 22

    svg.append('</svg>')
    output_path.write_text("\n".join(svg), encoding="utf-8")


def print_summary(episode: int, summary: Dict[str, dict]):
    print(f"Episode {episode} hz summary")
    for topic in TOPICS:
        label = TOPIC_LABELS[topic]
        avg = summary[topic]["avg"]
        min_v = summary[topic]["min"]
        max_v = summary[topic]["max"]
        print(f"- {topic} ({label})")
        if math.isfinite(avg):
            print(f"  avg: {avg:.3f} Hz")
            print(f"  min: {min_v:.3f} Hz")
            print(f"  max: {max_v:.3f} Hz")
            print(f"  range: {min_v:.3f} ~ {max_v:.3f} Hz")
        else:
            print("  avg: NaN")
            print("  min: NaN")
            print("  max: NaN")
            print("  range: NaN")


def main():
    args = parse_args()
    dataset_dir = Path(args.dataset_dir).expanduser()
    episode_dir = dataset_dir / f"episode{args.episode}"
    start, end, start_wall, end_wall = parse_capture_window(episode_dir / "capture_timing.log")
    records = load_records(dataset_dir / "capture_status_hz.log", start, end, start_wall, end_wall)
    summary = summarize(records)
    print_summary(args.episode, summary)
    output_svg = Path(args.output_svg).expanduser() if args.output_svg else episode_dir / "hz_summary.svg"
    build_svg(summary, end - start, output_svg)
    print(f"Saved plot to: {output_svg}")


if __name__ == "__main__":
    raise SystemExit(main())
