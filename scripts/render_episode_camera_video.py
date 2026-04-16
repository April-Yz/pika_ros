#!/usr/bin/env /usr/bin/python3

import argparse
import math
import os
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".npy"}


@dataclass
class FrameRef:
    timestamp: float
    path: Path


@dataclass
class CameraSource:
    label: str
    path: Path
    frames: List[FrameRef]

    @property
    def timestamps(self) -> List[float]:
        return [frame.timestamp for frame in self.frames]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render one or more episodes' available camera folders into stitched overview videos."
        )
    )
    parser.add_argument(
        "episodes",
        nargs="*",
        help=(
            "Episode paths or indexes. Examples: /home/piper/agilex/data/episode4 4 7. "
            "If omitted, all episode directories under --dataset-dir are rendered."
        ),
    )
    parser.add_argument(
        "--dataset-dir",
        default=None,
        help="Dataset root used when episode is given as an index. Overrides --task-name/--dataset-root.",
    )
    parser.add_argument(
        "--dataset-root",
        default=os.path.expanduser("~/agilex"),
        help="Dataset parent root used together with --task-name. Default: ~/agilex",
    )
    parser.add_argument(
        "--task-name",
        default="data",
        help="Task subdirectory under --dataset-root. Default: data",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output video path for a single episode. "
            "When rendering multiple episodes or all episodes, each episode writes to its own "
            "camera_overview.mp4 unless --overwrite is used."
        ),
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=20.0,
        help="Output video fps. Default: 20",
    )
    parser.add_argument(
        "--tile-width",
        type=int,
        default=640,
        help="Width of each camera tile. Default: 640",
    )
    parser.add_argument(
        "--tile-height",
        type=int,
        default=480,
        help="Height of each camera tile. Default: 480",
    )
    parser.add_argument(
        "--max-gap",
        type=float,
        default=0.25,
        help="Max timestamp gap in seconds allowed when matching frames across cameras. Default: 0.25",
    )
    parser.add_argument(
        "--include-depth",
        action="store_true",
        help="Also include depth camera folders if they contain image files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-render even if the output video already exists.",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional camera folder names to keep. Example: myD435 pikaGripperDepthCamera_l",
    )
    return parser.parse_args()


def resolve_dataset_dir(args: argparse.Namespace) -> str:
    if args.dataset_dir:
        return os.path.expanduser(args.dataset_dir)
    return os.path.expanduser(os.path.join(args.dataset_root, args.task_name))


def resolve_episode_path(episode: str, dataset_dir: str) -> Path:
    candidate = Path(episode).expanduser()
    if candidate.exists():
        return candidate
    if episode.isdigit():
        indexed = Path(dataset_dir).expanduser() / f"episode{episode}"
        if indexed.exists():
            return indexed
    raise FileNotFoundError(f"Episode not found: {episode}")


def discover_episode_dirs(dataset_dir: str) -> List[Path]:
    root = Path(dataset_dir).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root}")
    return sorted(
        [path for path in root.iterdir() if path.is_dir() and path.name.startswith("episode")],
        key=lambda path: (0, int(path.name[len("episode"):])) if path.name[len("episode"):].isdigit() else (1, path.name),
    )


def parse_timestamp(path: Path) -> Optional[float]:
    if path.suffix.lower() not in IMAGE_EXTS:
        return None
    if path.name == "config.json":
        return None
    try:
        return float(path.stem)
    except ValueError:
        return None


def load_sources(episode_dir: Path, include_depth: bool, only: Optional[Sequence[str]]) -> List[CameraSource]:
    roots = [episode_dir / "camera" / "color"]
    if include_depth:
        roots.append(episode_dir / "camera" / "depth")

    sources: List[CameraSource] = []
    for root in roots:
        if not root.is_dir():
            continue
        for camera_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if only and camera_dir.name not in only:
                continue
            frames: List[FrameRef] = []
            for file_path in sorted(camera_dir.iterdir()):
                timestamp = parse_timestamp(file_path)
                if timestamp is None:
                    continue
                frames.append(FrameRef(timestamp=timestamp, path=file_path))
            if frames:
                label = f"{root.name}/{camera_dir.name}"
                sources.append(CameraSource(label=label, path=camera_dir, frames=frames))
    if not sources:
        raise RuntimeError(f"No camera frames found under {episode_dir / 'camera'}")
    return sources


def choose_reference_source(sources: Sequence[CameraSource]) -> CameraSource:
    d435_sources = [source for source in sources if "d435" in source.label.lower()]
    if d435_sources:
        return max(d435_sources, key=lambda source: len(source.frames))
    return max(sources, key=lambda source: len(source.frames))


def build_timeline(reference: CameraSource, fps: float) -> List[float]:
    if not reference.frames:
        return []
    if fps <= 0:
        return reference.timestamps
    min_dt = 1.0 / fps
    timeline: List[float] = []
    last = -math.inf
    for timestamp in reference.timestamps:
        if timestamp - last >= min_dt * 0.95:
            timeline.append(timestamp)
            last = timestamp
    return timeline


def nearest_frame(source: CameraSource, timestamp: float, max_gap: float) -> Optional[Path]:
    stamps = source.timestamps
    if not stamps:
        return None
    idx = bisect_left(stamps, timestamp)
    candidates = []
    if idx < len(stamps):
        candidates.append(idx)
    if idx > 0:
        candidates.append(idx - 1)
    best_idx = None
    best_gap = None
    for candidate in candidates:
        gap = abs(stamps[candidate] - timestamp)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_idx = candidate
    if best_idx is None or best_gap is None or best_gap > max_gap:
        return None
    return source.frames[best_idx].path


def load_image(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        array = np.load(str(path))
        if array.ndim == 2:
            return normalize_depth_like(array)
        if array.ndim == 3 and array.shape[2] == 3:
            return to_bgr8(array)
        raise ValueError(f"Unsupported npy shape: {array.shape} from {path}")

    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Failed to read image: {path}")
    if image.ndim == 2:
        return normalize_depth_like(image)
    return to_bgr8(image)


def to_bgr8(image: np.ndarray) -> np.ndarray:
    if image.dtype != np.uint8:
        image = cv2.convertScaleAbs(image)
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 3:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    raise ValueError(f"Unsupported image shape: {image.shape}")


def normalize_depth_like(image: np.ndarray) -> np.ndarray:
    finite = image[np.isfinite(image)] if np.issubdtype(image.dtype, np.floating) else image
    if finite.size == 0:
        normalized = np.zeros(image.shape[:2], dtype=np.uint8)
    else:
        min_val = float(np.min(finite))
        max_val = float(np.max(finite))
        if max_val - min_val < 1e-9:
            normalized = np.zeros(image.shape[:2], dtype=np.uint8)
        else:
            scaled = (image.astype(np.float32) - min_val) * 255.0 / (max_val - min_val)
            normalized = np.clip(scaled, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)


def placeholder_tile(width: int, height: int, label: str, message: str) -> np.ndarray:
    tile = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(tile, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(tile, message, (20, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 255), 2, cv2.LINE_AA)
    return tile


def draw_tile(frame: Optional[Path], label: str, width: int, height: int) -> np.ndarray:
    if frame is None:
        return placeholder_tile(width, height, label, "no matched frame")
    image = load_image(frame)
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    cv2.rectangle(image, (0, 0), (width - 1, 55), (0, 0, 0), thickness=-1)
    cv2.putText(image, label, (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, frame.name, (14, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return image


def make_canvas(tiles: Sequence[np.ndarray], cols: int, tile_width: int, tile_height: int) -> np.ndarray:
    rows = math.ceil(len(tiles) / cols)
    canvas = np.zeros((rows * tile_height, cols * tile_width, 3), dtype=np.uint8)
    for index, tile in enumerate(tiles):
        row = index // cols
        col = index % cols
        y0 = row * tile_height
        x0 = col * tile_width
        canvas[y0:y0 + tile_height, x0:x0 + tile_width] = tile
    return canvas


def render_video(
    episode_dir: Path,
    sources: Sequence[CameraSource],
    output_path: Path,
    fps: float,
    tile_width: int,
    tile_height: int,
    max_gap: float,
) -> None:
    reference = choose_reference_source(sources)
    timeline = build_timeline(reference, fps)
    if not timeline:
        raise RuntimeError("No frames available to render.")

    cols = math.ceil(math.sqrt(len(sources)))
    rows = math.ceil(len(sources) / cols)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (cols * tile_width, rows * tile_height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer: {output_path}")

    try:
        for timestamp in timeline:
            tiles = []
            for source in sources:
                frame = nearest_frame(source, timestamp, max_gap=max_gap)
                tiles.append(draw_tile(frame, source.label, tile_width, tile_height))
            canvas = make_canvas(tiles, cols=cols, tile_width=tile_width, tile_height=tile_height)
            cv2.putText(
                canvas,
                f"{episode_dir.name}  t={timestamp:.6f}",
                (20, canvas.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            writer.write(canvas)
    finally:
        writer.release()


def should_skip_render(output_path: Path, overwrite: bool) -> bool:
    return output_path.exists() and not overwrite


def main() -> int:
    args = parse_args()
    dataset_dir = resolve_dataset_dir(args)
    if args.output and len(args.episodes) != 1:
        raise SystemExit("--output can only be used when rendering exactly one episode.")

    try:
        if args.episodes:
            episode_dirs = [resolve_episode_path(episode, dataset_dir) for episode in args.episodes]
        else:
            episode_dirs = discover_episode_dirs(dataset_dir)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    seen = set()
    unique_episode_dirs = []
    for episode_dir in episode_dirs:
        if episode_dir in seen:
            continue
        seen.add(episode_dir)
        unique_episode_dirs.append(episode_dir)

    if not unique_episode_dirs:
        raise SystemExit("No episode directories found to render.")

    rendered = []
    skipped = []
    failed = []

    for episode_dir in unique_episode_dirs:
        output_path = Path(args.output).expanduser() if args.output else episode_dir / "camera_overview.mp4"
        if should_skip_render(output_path, overwrite=args.overwrite):
            print(f"[skip] {episode_dir.name}: {output_path.name} already exists")
            skipped.append(episode_dir.name)
            continue

        try:
            sources = load_sources(episode_dir, include_depth=args.include_depth, only=args.only)
            render_video(
                episode_dir=episode_dir,
                sources=sources,
                output_path=output_path,
                fps=args.fps,
                tile_width=args.tile_width,
                tile_height=args.tile_height,
                max_gap=args.max_gap,
            )
        except Exception as exc:
            print(f"[fail] {episode_dir.name}: {exc}")
            failed.append(episode_dir.name)
            continue

        print(f"[ok]   {episode_dir.name}: {output_path}")
        print("  Included sources:")
        for source in sources:
            print(f"    - {source.label}: {len(source.frames)} frames")
        rendered.append(episode_dir.name)

    print("\nSummary")
    print(f"  rendered: {len(rendered)}")
    print(f"  skipped:  {len(skipped)}")
    print(f"  failed:   {len(failed)}")
    if rendered:
        print("  rendered list:", ", ".join(rendered))
    if skipped:
        print("  skipped list:", ", ".join(skipped))
    if failed:
        print("  failed list:", ", ".join(failed))

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
