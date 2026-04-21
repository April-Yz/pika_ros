#!/usr/bin/env python3
"""
Export preview images from a processed RobotWin-style HDF5 episode.

This avoids shell heredoc issues and helps diagnose RGB/BGR channel swaps.

For each selected camera/frame, the script writes:
- `<camera>_<idx>_decoded.jpg`: image decoded normally by OpenCV
- `<camera>_<idx>_channel_swapped.jpg`: red/blue channels swapped for comparison
- `<camera>_<idx>_compare.jpg`: decoded and channel-swapped side by side

Example:
python /home/piper/pika_ros/scripts/export_robotwin_hdf5_preview_images.py \
  /home/piper/agilex/processed_robotwin/pnp_star_pear-160/episode_0/episode_0.hdf5
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import cv2
import h5py
import numpy as np


DEFAULT_CAMERAS = ["cam_high", "cam_left_wrist", "cam_right_wrist"]


def decode_padded_jpeg(raw_item) -> np.ndarray:
    if isinstance(raw_item, np.bytes_):
        raw_item = bytes(raw_item)
    elif isinstance(raw_item, str):
        raw_item = raw_item.encode()
    raw_item = raw_item.rstrip(b"\0")
    image = cv2.imdecode(np.frombuffer(raw_item, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Failed to decode JPEG payload")
    return image


def selected_indices(length: int, requested: Iterable[int] | None) -> List[int]:
    if length <= 0:
        return []
    if requested:
        result = []
        for idx in requested:
            if idx < 0:
                idx = length + idx
            if 0 <= idx < length:
                result.append(idx)
            else:
                raise IndexError(f"frame index out of range: {idx}, length={length}")
        return sorted(set(result))
    return sorted(set([0, length // 2, length - 1]))


def add_label(image: np.ndarray, label: str) -> np.ndarray:
    out = image.copy()
    cv2.rectangle(out, (0, 0), (420, 34), (0, 0, 0), thickness=-1)
    cv2.putText(out, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def export_previews(hdf5_path: Path, output_dir: Path, cameras: List[str], indices: List[int] | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with h5py.File(hdf5_path, "r") as f:
        for camera in cameras:
            key = f"observations/images/{camera}"
            if key not in f:
                print(f"skip missing key: {key}")
                continue

            dataset = f[key]
            frame_indices = selected_indices(len(dataset), indices)
            print(f"{camera}: length={len(dataset)}, export_indices={frame_indices}")

            for idx in frame_indices:
                decoded = decode_padded_jpeg(dataset[idx])
                swapped = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)

                decoded_path = output_dir / f"{camera}_{idx:04d}_decoded.jpg"
                swapped_path = output_dir / f"{camera}_{idx:04d}_channel_swapped.jpg"
                compare_path = output_dir / f"{camera}_{idx:04d}_compare.jpg"

                cv2.imwrite(str(decoded_path), decoded)
                cv2.imwrite(str(swapped_path), swapped)

                compare = cv2.hconcat(
                    [
                        add_label(decoded, "decoded_by_opencv"),
                        add_label(swapped, "red_blue_channel_swapped"),
                    ]
                )
                cv2.imwrite(str(compare_path), compare)

    print(f"saved preview images to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export preview images from processed RobotWin HDF5.")
    parser.add_argument("hdf5_path", type=str, help="Path to episode HDF5 file")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory. Default: <episode_dir>/preview_images",
    )
    parser.add_argument(
        "--camera",
        action="append",
        choices=DEFAULT_CAMERAS,
        help="Camera to export. Can be repeated. Default: all cameras",
    )
    parser.add_argument(
        "--index",
        type=int,
        action="append",
        help="Frame index to export. Can be repeated. Default: first, middle, last",
    )
    args = parser.parse_args()

    hdf5_path = Path(args.hdf5_path).expanduser().resolve()
    if not hdf5_path.exists():
        raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else hdf5_path.parent / "preview_images"
    export_previews(hdf5_path, output_dir, args.camera or DEFAULT_CAMERAS, args.index)


if __name__ == "__main__":
    main()
