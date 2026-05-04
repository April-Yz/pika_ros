"""
将当前 `~/agilex/<task>/episode*` 原始采集目录转换为 RobotWin 风格的处理结果。

适用的数据来源：
- `pipline.sh` 的当前双臂遥操采集链
- 无 fisheye
- 额外包含一个头部 D435 RGB 相机

当前原始目录格式：
- `episodeN/camera/color/pikaGripperDepthCamera_l/*.jpg`
- `episodeN/camera/color/pikaGripperDepthCamera_r/*.jpg`
- `episodeN/camera/color/myD435/*.jpg`
- `episodeN/camera/depth/pikaGripperDepthCamera_l/*.png`
- `episodeN/camera/depth/pikaGripperDepthCamera_r/*.png`
- `episodeN/arm/endPose/puppetLeft/*.json`
- `episodeN/arm/endPose/puppetRight/*.json`
- `episodeN/arm/endPose/masterLeft/*.json`
- `episodeN/arm/endPose/masterRight/*.json`
- `episodeN/arm/jointState/*/*.json`
- `episodeN/gripper/encoder/pikaGripper_l/*.json`
- `episodeN/gripper/encoder/pikaGripper_r/*.json`
- `episodeN/gripper/encoder/pikaSensor_l/*.json`
- `episodeN/gripper/encoder/pikaSensor_r/*.json`
- `episodeN/localization/pose/pika_l/*.json` 定位器定位数据
- `episodeN/localization/pose/pika_r/*.json` 定位器定位数据
- `episodeN/instructions.json`
- `episodeN/statistic.txt`

本脚本中的固定语义映射：
- `camera/color/pikaGripperDepthCamera_l` -> 左手腕 RGB -> `cam_left_wrist`
- `camera/color/pikaGripperDepthCamera_r` -> 右手腕 RGB -> `cam_right_wrist`
- `camera/color/myD435` -> 头部 RGB -> `cam_high`

特别说明：
- 这里明确把 `myD435` 视为 `headCam`
- 当前 raw 数据没有独立的 action 字段，因此默认使用“下一时刻的 puppet 状态”作为 action
- 当前支持通过参数切换 gripper 数据源：
  - `--gripper-source robot` 使用 `pikaGripper_*`
  - `--gripper-source sensor` 使用 `pikaSensor_*`
- state 和 action 都采用：
  `[left_pos(3), left_euler(3), left_gripper(1), right_pos(3), right_euler(3), right_gripper(1)]`
- 也就是每步 14 维

当前脚本明确“未使用/舍弃”的原始字段：
- 舍弃双路 depth 图像：
  - `camera/depth/pikaGripperDepthCamera_l`
  - `camera/depth/pikaGripperDepthCamera_r`
- 舍弃 fisheye：
  - 当前采集链本身就没有 fisheye，本脚本也不处理 fisheye
- 舍弃 master 端末端位姿：
  - `arm/endPose/masterLeft`
  - `arm/endPose/masterRight`
- 舍弃 jointState：
  - `arm/jointState/masterLeft`
  - `arm/jointState/masterRight`
  - `arm/jointState/puppetLeft`
  - `arm/jointState/puppetRight`
- 舍弃 sensor 夹爪编码器：
  - 默认 `robot` 模式下舍弃 `gripper/encoder/pikaSensor_l`
  - 默认 `robot` 模式下舍弃 `gripper/encoder/pikaSensor_r`
- 舍弃 localization：
  - `localization/pose/pika_l`
  - `localization/pose/pika_r`
- 舍弃 episode 内已有的 `instructions.json`：
  - 当前处理脚本统一使用命令行传入的 task instruction

这样做的原因：
- 当前目标是生成最直接的 RobotWin 训练输入
- 先固定使用三路 RGB + puppet 端末端位姿 + gripper distance
- 减少字段分支，避免把当前任务无关信息混进 state
- 后续如果需要做异常检测、时序筛选、动作重建，再考虑把 depth、jointState、localization 作为辅助信号接回
- 如果真实部署时需要更大的夹持冗余，可以切换到 `sensor` gripper 源

示例：
python /home/piper/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_star_pear \
  "Pick up the starfruit and the pear, then place them onto the blue plate." \
  50

指定输出目录：
python /home/piper/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_star_pear \
  "Pick up the starfruit and the pear, then place them onto the blue plate." \
  50 \
  --output-dir /home/piper/agilex/processed_robotwin/pnp_star_pear-50

使用 sensor gripper：
python /home/piper/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_star_pear \
  "Pick up the starfruit and the pear, then place them onto the blue plate." \
  50 \
  --gripper-source sensor

对比单个 episode 的 robot/sensor gripper：
python /home/piper/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_star_pear \
  "Pick up the starfruit and the pear, then place them onto the blue plate." \
  1 \
  --compare-gripper-episode 147
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

try:
    import h5py
except ModuleNotFoundError:
    h5py = None


HEAD_CAM_DIRNAME = "myD435"
HEAD_CAM_KEY = "headCam"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
TARGET_RGB_HZ = 10.0
MIN_RGB_HZ = 8.0


@dataclass(frozen=True)
class EpisodePaths:
    episode_dir: Path
    left_wrist_rgb: Path
    right_wrist_rgb: Path
    head_rgb: Path
    puppet_left_pose: Path
    puppet_right_pose: Path
    gripper_robot_left: Path
    gripper_robot_right: Path
    gripper_sensor_left: Path
    gripper_sensor_right: Path


@dataclass(frozen=True)
class AuditResult:
    level: str
    reason: str
    detail: str


def parse_timestamp_from_name(path: Path) -> float:
    return float(path.stem)


def list_timestamped_files(path: Path, suffix: str) -> List[Path]:
    if not path.exists():
        return []
    files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() == suffix]
    return sorted(files, key=parse_timestamp_from_name)


def load_pose_json(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return np.array(
        [
            float(data["x"]),
            float(data["y"]),
            float(data["z"]),
            float(data["roll"]),
            float(data["pitch"]),
            float(data["yaw"]),
        ],
        dtype=np.float32,
    )


def load_gripper_json(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return np.array([float(data["distance"])], dtype=np.float32)


def nearest_path(files: List[Path], target_ts: float) -> Path:
    if not files:
        raise ValueError("nearest_path received an empty file list")
    return min(files, key=lambda p: abs(parse_timestamp_from_name(p) - target_ts))


def read_and_resize_rgb(path: Path, image_size: Tuple[int, int]) -> np.ndarray:
    if cv2 is None:
        raise ModuleNotFoundError("cv2 is required for image processing mode")
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Failed to read image: {path}")
    width, height = image_size
    if image.shape[1] != width or image.shape[0] != height:
        image = cv2.resize(image, (width, height))
    return image


def images_encoding(imgs: List[np.ndarray]) -> Tuple[List[bytes], int]:
    if cv2 is None:
        raise ModuleNotFoundError("cv2 is required for image encoding mode")
    encoded = []
    max_len = 0
    for image in imgs:
        ok, encoded_image = cv2.imencode(".jpg", image)
        if not ok:
            raise RuntimeError("Failed to JPEG-encode an image")
        jpeg_data = encoded_image.tobytes()
        encoded.append(jpeg_data)
        max_len = max(max_len, len(jpeg_data))
    padded = [item.ljust(max_len, b"\0") for item in encoded]
    return padded, max_len


def build_episode_paths(episode_dir: Path) -> EpisodePaths:
    return EpisodePaths(
        episode_dir=episode_dir,
        left_wrist_rgb=episode_dir / "camera" / "color" / "pikaGripperDepthCamera_l",
        right_wrist_rgb=episode_dir / "camera" / "color" / "pikaGripperDepthCamera_r",
        head_rgb=episode_dir / "camera" / "color" / HEAD_CAM_DIRNAME,
        puppet_left_pose=episode_dir / "arm" / "endPose" / "puppetLeft",
        puppet_right_pose=episode_dir / "arm" / "endPose" / "puppetRight",
        gripper_robot_left=episode_dir / "gripper" / "encoder" / "pikaGripper_l",
        gripper_robot_right=episode_dir / "gripper" / "encoder" / "pikaGripper_r",
        gripper_sensor_left=episode_dir / "gripper" / "encoder" / "pikaSensor_l",
        gripper_sensor_right=episode_dir / "gripper" / "encoder" / "pikaSensor_r",
    )


def selected_gripper_paths(paths: EpisodePaths, gripper_source: str) -> Tuple[Path, Path]:
    if gripper_source == "sensor":
        return paths.gripper_sensor_left, paths.gripper_sensor_right
    if gripper_source == "robot":
        return paths.gripper_robot_left, paths.gripper_robot_right
    raise ValueError(f"Unsupported gripper_source: {gripper_source}")


def log_audit(log_path: Path, episode_name: str, level: str, reason: str, detail: str) -> None:
    record = {
        "episode": episode_name,
        "level": level,
        "reason": reason,
        "detail": detail,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_colored(level: str, message: str) -> None:
    if level == "ERROR":
        print(f"{RED}{message}{RESET}")
    elif level == "WARNING":
        print(f"{YELLOW}{message}{RESET}")
    else:
        print(message)


def rgb_file_counts(paths: EpisodePaths) -> Dict[str, int]:
    return {
        "cam_left_wrist": len(list_timestamped_files(paths.left_wrist_rgb, ".jpg")),
        "cam_right_wrist": len(list_timestamped_files(paths.right_wrist_rgb, ".jpg")),
        "cam_high": len(list_timestamped_files(paths.head_rgb, ".jpg")),
        "state_left_pose": len(list_timestamped_files(paths.puppet_left_pose, ".json")),
        "state_right_pose": len(list_timestamped_files(paths.puppet_right_pose, ".json")),
        "robot_left_gripper": len(list_timestamped_files(paths.gripper_robot_left, ".json")),
        "robot_right_gripper": len(list_timestamped_files(paths.gripper_robot_right, ".json")),
        "sensor_left_gripper": len(list_timestamped_files(paths.gripper_sensor_left, ".json")),
        "sensor_right_gripper": len(list_timestamped_files(paths.gripper_sensor_right, ".json")),
    }


def check_structure(paths: EpisodePaths, gripper_source: str) -> Optional[AuditResult]:
    counts = rgb_file_counts(paths)
    required = [
        "cam_left_wrist",
        "cam_right_wrist",
        "cam_high",
        "state_left_pose",
        "state_right_pose",
    ]
    if gripper_source == "sensor":
        required.extend(["sensor_left_gripper", "sensor_right_gripper"])
    else:
        required.extend(["robot_left_gripper", "robot_right_gripper"])
    missing = [name for name in required if counts[name] <= 1]
    if missing:
        detail = ", ".join([f"{name}={counts[name]}" for name in missing])
        return AuditResult(
            level="ERROR",
            reason="missing_required_data",
            detail=detail,
        )
    return None


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
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            key = parts[0]
            if key not in keys:
                continue
            try:
                hz_map[key] = float(parts[-1])
            except ValueError:
                continue
    if len(hz_map) != len(keys):
        return None
    return hz_map


def check_rgb_hz(episode_dir: Path) -> Optional[AuditResult]:
    hz_map = parse_episode_rgb_hz(episode_dir)
    if hz_map is None:
        return AuditResult(
            level="WARNING",
            reason="missing_rgb_hz_stat",
            detail="statistic.txt missing or RGB hz entries incomplete",
        )

    min_key = min(hz_map, key=hz_map.get)
    min_hz = hz_map[min_key]
    detail = ", ".join([f"{k}={v:.3f}" for k, v in hz_map.items()])
    if min_hz < MIN_RGB_HZ:
        return AuditResult(
            level="ERROR",
            reason="rgb_hz_too_low",
            detail=f"min_rgb_hz={min_hz:.3f} on {min_key}; {detail}",
        )
    if min_hz < TARGET_RGB_HZ:
        return AuditResult(
            level="WARNING",
            reason="rgb_hz_below_target",
            detail=f"min_rgb_hz={min_hz:.3f} on {min_key}; {detail}",
        )
    return None


def valid_episode_dirs(dataset_dir: Path) -> List[Path]:
    pattern = re.compile(r"episode(\d+)$")
    candidates = []
    for path in dataset_dir.iterdir():
        if not path.is_dir():
            continue
        match = pattern.fullmatch(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    return [path for _, path in sorted(candidates)]


def align_episode(paths: EpisodePaths, image_size: Tuple[int, int], gripper_source: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, List[np.ndarray]]]:
    left_rgb_files = list_timestamped_files(paths.left_wrist_rgb, ".jpg")
    right_rgb_files = list_timestamped_files(paths.right_wrist_rgb, ".jpg")
    head_rgb_files = list_timestamped_files(paths.head_rgb, ".jpg")
    left_pose_files = list_timestamped_files(paths.puppet_left_pose, ".json")
    right_pose_files = list_timestamped_files(paths.puppet_right_pose, ".json")
    left_gripper_path, right_gripper_path = selected_gripper_paths(paths, gripper_source)
    left_gripper_files = list_timestamped_files(left_gripper_path, ".json")
    right_gripper_files = list_timestamped_files(right_gripper_path, ".json")

    reference_files = head_rgb_files
    if len(reference_files) < 2:
        raise RuntimeError(f"Not enough headCam frames in {paths.episode_dir}")

    aligned_states = []
    images = {
        "cam_high": [],
        "cam_left_wrist": [],
        "cam_right_wrist": [],
    }

    for head_path in reference_files:
        ts = parse_timestamp_from_name(head_path)
        left_pose = load_pose_json(nearest_path(left_pose_files, ts))
        right_pose = load_pose_json(nearest_path(right_pose_files, ts))
        left_gripper = load_gripper_json(nearest_path(left_gripper_files, ts))
        right_gripper = load_gripper_json(nearest_path(right_gripper_files, ts))

        state = np.concatenate([left_pose, left_gripper, right_pose, right_gripper], axis=0).astype(np.float32)
        aligned_states.append(state)

        images["cam_high"].append(read_and_resize_rgb(head_path, image_size))
        images["cam_left_wrist"].append(read_and_resize_rgb(nearest_path(left_rgb_files, ts), image_size))
        images["cam_right_wrist"].append(read_and_resize_rgb(nearest_path(right_rgb_files, ts), image_size))

    state_all = np.stack(aligned_states, axis=0)
    state_list = state_all[:-1]
    action_list = state_all[1:]

    trimmed_images = {
        "cam_high": images["cam_high"][:-1],
        "cam_left_wrist": images["cam_left_wrist"][:-1],
        "cam_right_wrist": images["cam_right_wrist"][:-1],
    }
    return state_list, action_list, trimmed_images


def summarize_values(values: np.ndarray) -> Dict[str, float]:
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def compare_gripper_episode(paths: EpisodePaths) -> Dict[str, object]:
    def load_series(source_path: Path) -> np.ndarray:
        files = list_timestamped_files(source_path, ".json")
        values = [load_gripper_json(p)[0] for p in files]
        return np.array(values, dtype=np.float32)

    robot_left = load_series(paths.gripper_robot_left)
    robot_right = load_series(paths.gripper_robot_right)
    sensor_left = load_series(paths.gripper_sensor_left)
    sensor_right = load_series(paths.gripper_sensor_right)

    min_left = min(len(robot_left), len(sensor_left))
    min_right = min(len(robot_right), len(sensor_right))

    left_diff = sensor_left[:min_left] - robot_left[:min_left] if min_left > 0 else np.array([], dtype=np.float32)
    right_diff = sensor_right[:min_right] - robot_right[:min_right] if min_right > 0 else np.array([], dtype=np.float32)

    result: Dict[str, object] = {
        "episode": paths.episode_dir.name,
        "robot_left": summarize_values(robot_left) if len(robot_left) else None,
        "sensor_left": summarize_values(sensor_left) if len(sensor_left) else None,
        "robot_right": summarize_values(robot_right) if len(robot_right) else None,
        "sensor_right": summarize_values(sensor_right) if len(sensor_right) else None,
        "left_aligned_count": int(min_left),
        "right_aligned_count": int(min_right),
        "left_sensor_minus_robot": summarize_values(left_diff) if len(left_diff) else None,
        "right_sensor_minus_robot": summarize_values(right_diff) if len(right_diff) else None,
    }
    return result


def save_robotwin_episode(
    save_dir: Path,
    episode_idx: int,
    instruction: str,
    state_list: np.ndarray,
    action_list: np.ndarray,
    image_dict: Dict[str, List[np.ndarray]],
) -> None:
    if h5py is None:
        raise ModuleNotFoundError("h5py is required for HDF5 export mode")
    episode_save_path = save_dir / f"episode_{episode_idx}"
    episode_save_path.mkdir(parents=True, exist_ok=True)

    with (episode_save_path / "instructions.json").open("w", encoding="utf-8") as f:
        json.dump({"instructions": [instruction]}, f, indent=2, ensure_ascii=False)

    hdf5_path = episode_save_path / f"episode_{episode_idx}.hdf5"
    with h5py.File(hdf5_path, "w") as f:
        f.create_dataset("action", data=action_list.astype(np.float32))
        obs = f.create_group("observations")
        obs.create_dataset("state", data=state_list.astype(np.float32))
        obs.create_dataset("left_arm_dim", data=np.full(len(action_list), 7, dtype=np.int32))
        obs.create_dataset("right_arm_dim", data=np.full(len(action_list), 7, dtype=np.int32))

        image_group = obs.create_group("images")
        for key in ["cam_high", "cam_left_wrist", "cam_right_wrist"]:
            encoded, max_len = images_encoding(image_dict[key])
            image_group.create_dataset(key, data=encoded, dtype=f"S{max_len}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Process current raw dual-arm teleop episodes into RobotWin-style HDF5. "
            "RGB mapping is fixed as left wrist / right wrist / headCam."
        )
    )
    parser.add_argument("dataset_dir", type=str, help="Task dataset directory, e.g. /home/piper/agilex/pnp_star_pear")
    parser.add_argument("instruction", type=str, help='Task description, e.g. "Pick up the starfruit and the pear, then place them onto the blue plate."')
    parser.add_argument("expert_data_num", type=int, help="Number of non-empty episodes to process")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory. Default: processed_data/<task_name>-<expert_data_num>",
    )
    parser.add_argument(
        "--image-width",
        type=int,
        default=640,
        help="Output RGB width. Default: 640",
    )
    parser.add_argument(
        "--image-height",
        type=int,
        default=480,
        help="Output RGB height. Default: 480",
    )
    parser.add_argument(
        "--gripper-source",
        choices=["robot", "sensor"],
        default="robot",
        help="Which gripper encoder source to use in state/action. Default: robot",
    )
    parser.add_argument(
        "--compare-gripper-episode",
        type=int,
        default=None,
        help="If set, only compare robot vs sensor gripper values for one episode index and print/save stats.",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).expanduser().resolve()
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    task_name = dataset_dir.name
    output_dir = Path(args.output_dir) if args.output_dir else Path("processed_data") / f"{task_name}-{args.expert_data_num}"
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_log_path = output_dir / "processing_audit.jsonl"
    comparison_log_path = output_dir / "gripper_comparison.json"

    print(f"read raw episodes from path: {dataset_dir}")
    print(f"task name: {task_name}")
    print(f"instruction: {args.instruction}")
    print(f"headCam source directory: {HEAD_CAM_DIRNAME}")
    print("rgb mapping: left wrist -> pikaGripperDepthCamera_l, right wrist -> pikaGripperDepthCamera_r, headCam -> myD435")
    print("action source: next-step puppet state")
    print(f"gripper source: {args.gripper_source}")

    if args.compare_gripper_episode is not None:
        target_episode_dir = dataset_dir / f"episode{args.compare_gripper_episode}"
        if not target_episode_dir.exists():
            raise FileNotFoundError(f"Episode directory not found: {target_episode_dir}")
        paths = build_episode_paths(target_episode_dir)
        result = compare_gripper_episode(paths)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        with comparison_log_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"saved gripper comparison to: {comparison_log_path}")
        return

    processed = 0
    for episode_dir in valid_episode_dirs(dataset_dir):
        if processed >= args.expert_data_num:
            break

        paths = build_episode_paths(episode_dir)
        structure_issue = check_structure(paths, args.gripper_source)
        if structure_issue is not None:
            print_colored(
                structure_issue.level,
                f"skip {episode_dir.name}: {structure_issue.reason}: {structure_issue.detail}",
            )
            log_audit(
                audit_log_path,
                episode_dir.name,
                structure_issue.level,
                structure_issue.reason,
                structure_issue.detail,
            )
            continue

        hz_issue = check_rgb_hz(episode_dir)
        if hz_issue is not None:
            print_colored(
                hz_issue.level,
                f"{'skip' if hz_issue.level == 'ERROR' else 'warn'} {episode_dir.name}: "
                f"{hz_issue.reason}: {hz_issue.detail}",
            )
            log_audit(
                audit_log_path,
                episode_dir.name,
                hz_issue.level,
                hz_issue.reason,
                hz_issue.detail,
            )
            if hz_issue.level == "ERROR":
                continue

        state_list, action_list, image_dict = align_episode(paths, (args.image_width, args.image_height), args.gripper_source)
        if len(state_list) == 0 or len(action_list) == 0:
            reason = "empty_state_or_action"
            detail = f"state_len={len(state_list)}, action_len={len(action_list)}"
            print_colored("ERROR", f"skip {episode_dir.name}: {reason}: {detail}")
            log_audit(audit_log_path, episode_dir.name, "ERROR", reason, detail)
            continue

        save_robotwin_episode(output_dir, processed, args.instruction, state_list, action_list, image_dict)
        processed += 1
        print(f"processed {episode_dir.name} -> episode_{processed - 1}")

    print(f"done, total processed episodes: {processed}")
    print(f"audit log: {audit_log_path}")


if __name__ == "__main__":
    main()
