"""
检查 `process_data_robotwin_headcam.py` 生成的 RobotWin 风格数据内容。

检查项：
- 输出目录结构是否存在
- `instructions.json` 是否存在
- HDF5 是否存在
- `action` / `observations/state` 是否存在且长度一致
- 图像 key 是否存在：
  - `observations/images/cam_high`
  - `observations/images/cam_left_wrist`
  - `observations/images/cam_right_wrist`
- 统计 state/action/image 的 shape 和 dtype
- 抽样解码 JPEG，确认不是空字节

示例：
python /home/piper/pika_ros/scripts/check_processed_robotwin_headcam.py \
  /home/piper/agilex/processed_robotwin/pnp_star_pear-50 \
  --episode 0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import h5py
import numpy as np


def decode_padded_jpeg(raw_item) -> np.ndarray:
    if isinstance(raw_item, np.bytes_):
        raw_item = bytes(raw_item)
    elif isinstance(raw_item, str):
        raw_item = raw_item.encode()
    raw_item = raw_item.rstrip(b"\0")
    image = cv2.imdecode(np.frombuffer(raw_item, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("failed to decode JPEG payload")
    return image


def inspect_episode(base_dir: Path, episode_idx: int) -> None:
    episode_dir = base_dir / f"episode_{episode_idx}"
    instruction_path = episode_dir / "instructions.json"
    hdf5_path = episode_dir / f"episode_{episode_idx}.hdf5"

    print(f"episode_dir: {episode_dir}")
    print(f"instructions_exists: {instruction_path.exists()}")
    print(f"hdf5_exists: {hdf5_path.exists()}")

    if instruction_path.exists():
        with instruction_path.open("r", encoding="utf-8") as f:
            instructions = json.load(f)
        print(f"instructions_json: {instructions}")

    if not hdf5_path.exists():
        raise FileNotFoundError(f"missing HDF5: {hdf5_path}")

    with h5py.File(hdf5_path, "r") as f:
        action = f["action"]
        state = f["observations/state"]
        left_dim = f["observations/left_arm_dim"]
        right_dim = f["observations/right_arm_dim"]
        cam_high = f["observations/images/cam_high"]
        cam_left = f["observations/images/cam_left_wrist"]
        cam_right = f["observations/images/cam_right_wrist"]

        print("keys:")
        f.visit(lambda name: print(f"  {name}"))

        print(f"action shape={action.shape} dtype={action.dtype}")
        print(f"state shape={state.shape} dtype={state.dtype}")
        print(f"left_arm_dim shape={left_dim.shape} dtype={left_dim.dtype}")
        print(f"right_arm_dim shape={right_dim.shape} dtype={right_dim.dtype}")
        print(f"cam_high shape={cam_high.shape} dtype={cam_high.dtype}")
        print(f"cam_left_wrist shape={cam_left.shape} dtype={cam_left.dtype}")
        print(f"cam_right_wrist shape={cam_right.shape} dtype={cam_right.dtype}")

        if len(action) != len(state):
            raise RuntimeError(f"length mismatch: action={len(action)} state={len(state)}")
        if len(cam_high) != len(state) or len(cam_left) != len(state) or len(cam_right) != len(state):
            raise RuntimeError("image sequence length does not match state length")

        print("sample values:")
        print(f"state[0]={state[0].tolist()}")
        print(f"action[0]={action[0].tolist()}")

        for name, ds in [
            ("cam_high", cam_high),
            ("cam_left_wrist", cam_left),
            ("cam_right_wrist", cam_right),
        ]:
            image = decode_padded_jpeg(ds[0])
            print(f"{name} decoded shape={image.shape} dtype={image.dtype}")

        print("check result: OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect processed RobotWin-format headCam dataset output.")
    parser.add_argument("processed_dir", type=str, help="Processed output directory, e.g. /home/piper/agilex/processed_robotwin/pnp_star_pear-50")
    parser.add_argument("--episode", type=int, default=0, help="Episode index in processed directory. Default: 0")
    args = parser.parse_args()

    inspect_episode(Path(args.processed_dir).expanduser().resolve(), args.episode)


if __name__ == "__main__":
    main()
