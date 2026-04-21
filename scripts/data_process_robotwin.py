"""
这个脚本处理的是“旧 R1 中间 H5 格式”，不是当前 `~/agilex/<task>/episode*`
这种原始采集目录。

输入格式：
- 目录下是一批 `.h5` 文件
- 每个 `.h5` 已经整理成 R1 风格结构
- 典型字段包括：
  - `/obs/arm_left/eef_pos`
  - `/obs/arm_left/eef_euler`
  - `/obs/gripper_left/joint_pos`
  - `/obs/arm_right/eef_pos`
  - `/obs/arm_right/eef_euler`
  - `/obs/gripper_right/joint_pos`
  - `/action/arm_left/eef_pos`
  - `/action/arm_left/eef_euler`
  - `/action/gripper_left/commanded_pos`
  - `/action/arm_right/eef_pos`
  - `/action/arm_right/eef_euler`
  - `/action/gripper_right/commanded_pos`
  - `/obs/<camera_name>/rgb`

输出格式：
- `processed_data/<task_name>-<episode_num>/episode_i/episode_i.hdf5`
- HDF5 中的关键字段包括：
  - `action`
  - `observations/state`
  - `observations/left_arm_dim`
  - `observations/right_arm_dim`
  - `observations/images/cam_high`
  - `observations/images/cam_left_wrist`
  - `observations/images/cam_right_wrist`

特别说明：
- 这个旧脚本默认约定：
  - `cam_high` 是头部主视角
  - `cam_left_wrist` 是左手腕 RGB
  - `cam_right_wrist` 是右手腕 RGB
- 它不直接读取当前新的原始采集目录
- 当前新的原始采集目录请使用新的独立脚本处理

# 默认使用 eepose 模式、手腕相机和默认路径
python process_data_R1.py task_name "pour water into the cup" 50

# 禁用手腕相机
python process_data_R1.py task_name "pour water into the cup" 50 --no-wrist

# 使用自定义数据路径
python process_data_R1.py task_name "pour water into the cup" 50 --load-dir /custom/path

# 切换到 qpos 模式
python process_data_R1.py task_name "pour water into the cup" 50 --use-qpos

# 同时指定自定义路径和 qpos 模式
python process_data_R1.py task_name "pour water into the cup" 50 --load-dir /custom/path --use-qpos
"""

import sys

import os
import h5py
import numpy as np
import pickle
import cv2
import argparse
import yaml, json
from scipy.spatial.transform import Rotation



import numpy as np
from scipy.spatial.transform import Rotation

def quaternion_to_euler(quat, order='xyz'):
    """
    将四元数转换为欧拉角，默认输入格式为 (w, x, y, z)。
    
    Args:
        quat: 四元数，shape (4,) 或 (N, 4)，默认假设格式为 (w, x, y, z)
        order: 欧拉角顺序，默认 'xyz'
    
    Returns:
        欧拉角，shape (3,) 或 (N, 3)
    """
    quat = np.array(quat)
    original_shape = quat.shape
    
    # 统一处理为 2D 数组 (N, 4)
    if quat.ndim == 1:
        quat = quat.reshape(1, -1)
        was_1d = True
    else:
        was_1d = False
    
    # 1. 归一化四元数 (防止非单位四元数导致计算错误)
    # 避免除以 0
    norms = np.linalg.norm(quat, axis=1, keepdims=True)
    quat_normalized = quat / (norms + 1e-8) 
    
    # 2. 格式警告检查 (Heuristic 启发式检查)
    # 逻辑：对于大多数实际应用（如机器人、动作捕捉），四元数通常接近单位阵。
    # 在 (w,x,y,z) 中，w 通常较大 (接近1或-1)。
    # 在 (x,y,z,w) 中，w 在最后，所以最后一个元素较大。
    # 如果最后一个元素的平均绝对值 显著大于 第一个元素，极大概率用户传错了格式。
    first_comp_abs_mean = np.abs(quat_normalized[:, 0]).mean()
    last_comp_abs_mean = np.abs(quat_normalized[:, -1]).mean()
    
    if last_comp_abs_mean > first_comp_abs_mean:
        # ANSI 转义序列：\033[91m 是亮红色，\033[0m 是重置颜色
        print(f"\033[91m[WARNING] 输入数据疑似为 (x,y,z,w) 格式，但当前函数强制按 (w,x,y,z) 解析！\n"
              f"          请检查输入数据源。Mean(First): {first_comp_abs_mean:.4f}, Mean(Last): {last_comp_abs_mean:.4f}\033[0m")

    # 3. 格式转换
    # 输入是 (w, x, y, z) -> [0, 1, 2, 3]
    # Scipy Rotation 需要 (x, y, z, w) -> [1, 2, 3, 0]
    quat_xyzw_for_scipy = quat_normalized[:, [1, 2, 3, 0]]
    
    # 4. 计算欧拉角
    rot = Rotation.from_quat(quat_xyzw_for_scipy)
    euler = rot.as_euler(order, degrees=False)
    
    if was_1d:
        return euler[0]
    return euler

def load_hdf5(dataset_path):
    """
    从 HDF5 文件加载 R1 数据
    
    Args:
        dataset_path: HDF5 文件路径
    
    Returns:
        state_all, action_all, image_dict
    """
    if not os.path.isfile(dataset_path):
        print(f"Dataset does not exist at \n{dataset_path}\n")
        exit()

    with h5py.File(dataset_path, "r") as root:
        # State (obs)
        obs_left_pos = root["/obs/arm_left/eef_pos"][()]
        obs_left_euler = root["/obs/arm_left/eef_euler"][()]
        obs_left_gripper = root["/obs/gripper_left/joint_pos"][()] / 100.0
        
        obs_right_pos = root["/obs/arm_right/eef_pos"][()]
        obs_right_euler = root["/obs/arm_right/eef_euler"][()]
        obs_right_gripper = root["/obs/gripper_right/joint_pos"][()] / 100.0

        # Action
        action_left_pos = root["/action/arm_left/eef_pos"][()]
        action_left_euler = root["/action/arm_left/eef_euler"][()]
        action_left_gripper = root["/action/gripper_left/commanded_pos"][()] / 100.0

        action_right_pos = root["/action/arm_right/eef_pos"][()]
        action_right_euler = root["/action/arm_right/eef_euler"][()]
        action_right_gripper = root["/action/gripper_right/commanded_pos"][()] / 100.0

        # 拼接 state: [left_pos, left_euler, left_gripper, right_pos, right_euler, right_gripper]
        # (N, 3+3+1+3+3+1) = (N, 14)
        state_all = np.concatenate([
            obs_left_pos, obs_left_euler, obs_left_gripper,
            obs_right_pos, obs_right_euler, obs_right_gripper
        ], axis=1).astype(np.float32)

        # 拼接 action: [left_pos, left_euler, left_gripper, right_pos, right_euler, right_gripper]
        # (N, 3+3+1+3+3+1) = (N, 14)
        action_all = np.concatenate([
            action_left_pos, action_left_euler, action_left_gripper.reshape(-1, 1),
            action_right_pos, action_right_euler, action_right_gripper.reshape(-1, 1)
        ], axis=1).astype(np.float32)

        image_dict = dict()
        # 确保 /obs/ 存在
        if "/obs" in root:
            # 遍历 /obs/ 下的所有相机
            for cam_name in root["/obs"].keys():
                if isinstance(root[f"/obs/{cam_name}"], h5py.Group) and 'rgb' in root[f"/obs/{cam_name}"]:
                    image_dict[cam_name] = root[f"/obs/{cam_name}/rgb"][()]
        # # ...
        # obs_left_gripper = root["/obs/gripper_left/joint_pos"][()]
        # obs_right_gripper = root["/obs/gripper_right/joint_pos"][()]
        # action_left_gripper = root["/action/gripper_left/commanded_pos"][()]
        # action_right_gripper = root["/action/gripper_right/commanded_pos"][()]

        # # 打印夹爪开合度范围
        # print(f"  Gripper Value Range in {os.path.basename(dataset_path)}:")
        # print(f"    State Left Gripper (obs):  min={np.min(obs_left_gripper):.4f}, max={np.max(obs_left_gripper):.4f}")
        # print(f"    State Right Gripper (obs): min={np.min(obs_right_gripper):.4f}, max={np.max(obs_right_gripper):.4f}")
        # print(f"    Action Left Gripper:       min={np.min(action_left_gripper):.4f}, max={np.max(action_left_gripper):.4f}")
        # print(f"    Action Right Gripper:      min={np.min(action_right_gripper):.4f}, max={np.max(action_right_gripper):.4f}")
        # # ...
    return state_all, action_all, image_dict


def images_encoding(imgs):
    encode_data = []
    padded_data = []
    max_len = 0
    for i in range(len(imgs)):
        success, encoded_image = cv2.imencode(".jpg", imgs[i])
        jpeg_data = encoded_image.tobytes()
        encode_data.append(jpeg_data)
        max_len = max(max_len, len(jpeg_data))
    # padding
    for i in range(len(imgs)):
        padded_data.append(encode_data[i].ljust(max_len, b"\0"))
    return encode_data, max_len


def get_task_config(task_name):
    with open(f"./task_config/{task_name}.yml", "r", encoding="utf-8") as f:
        args = yaml.load(f.read(), Loader=yaml.FullLoader)
    return args


def data_transform(path, episode_num, save_path, task_name, instructions, use_wrist=False):
    begin = 0
    h5_files = sorted([f for f in os.listdir(path) if f.endswith('.h5')])

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    for i, h5_file in enumerate(h5_files):
        if i >= episode_num:
            break

        print(f"Processing file: {h5_file}")
        
        # 使用传入的 instructions
        save_instructions_json = {"instructions": [instructions]}

        episode_save_path = os.path.join(save_path, f"episode_{i}")
        os.makedirs(episode_save_path, exist_ok=True)

        with open(os.path.join(episode_save_path, "instructions.json"), "w") as f:
            json.dump(save_instructions_json, f, indent=2)

        state_all, action_all, image_dict = load_hdf5(os.path.join(path, h5_file))
        
        num_steps = state_all.shape[0]

        # state_all 已经是 (N, 16) 的正确格式
        # action_all 已经是 (N, 14) 的正确格式
        
        # 在这个新逻辑中，state_list 就是 state_all 去掉最后一步
        # actions 就是 action_all 去掉第一步
        state_list = state_all[:-1]
        actions = action_all[1:]

        # 确认维度
        # state: [left_pos, left_euler, left_gripper, right_pos, right_euler, right_gripper]
        # (3+3+1+3+3+1) = 14
        left_arm_dim_val = 7 # pos+euler+gripper
        right_arm_dim_val = 7 # pos+euler+gripper

        cam_high = []
        cam_right_wrist = [] if use_wrist else None
        cam_left_wrist = [] if use_wrist else None
        
        # 图像处理
        for j in range(num_steps - 1):
            camera_high_bits = image_dict["camera_head"][j]
            # 真实数据已经是解码后的 numpy 数组
            camera_high = camera_high_bits 
            camera_high_resized = cv2.resize(camera_high, (640, 480))
            cam_high.append(camera_high_resized)

            if use_wrist:
                if "camera_right" in image_dict:
                    camera_right_wrist_bits = image_dict["camera_right"][j]
                    camera_right_wrist = camera_right_wrist_bits
                    camera_right_wrist_resized = cv2.resize(camera_right_wrist, (640, 480))
                    cam_right_wrist.append(camera_right_wrist_resized)

                if "camera_left" in image_dict:
                    camera_left_wrist_bits = image_dict["camera_left"][j]
                    camera_left_wrist = camera_left_wrist_bits
                    camera_left_wrist_resized = cv2.resize(camera_left_wrist, (640, 480))
                    cam_left_wrist.append(camera_left_wrist_resized)

        hdf5path = os.path.join(episode_save_path, f"episode_{i}.hdf5")

        with h5py.File(hdf5path, "w") as f:
            f.create_dataset("action", data=np.array(actions))
            obs = f.create_group("observations")
            
            # 存储 state
            obs.create_dataset("state", data=np.array(state_list))
            
            # 存储维度信息，注意这里是每个手臂的维度
            obs.create_dataset("left_arm_dim", data=np.full(len(actions), left_arm_dim_val))
            obs.create_dataset("right_arm_dim", data=np.full(len(actions), right_arm_dim_val))

            image = obs.create_group("images")
            cam_high_enc, len_high = images_encoding(cam_high)
            image.create_dataset("cam_high", data=cam_high_enc, dtype=f"S{len_high}")
            
            if use_wrist:
                if cam_right_wrist:
                    cam_right_wrist_enc, len_right = images_encoding(cam_right_wrist)
                    image.create_dataset("cam_right_wrist", data=cam_right_wrist_enc, dtype=f"S{len_right}")
                if cam_left_wrist:
                    cam_left_wrist_enc, len_left = images_encoding(cam_left_wrist)
                    image.create_dataset("cam_left_wrist", data=cam_left_wrist_enc, dtype=f"S{len_left}")

        begin += 1
        print(f"proccess {i} success!")

    return begin


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some episodes.")
    parser.add_argument(
        "task_name",
        type=str,
        default="beat_block_hammer",
        help="The name of the task (e.g., beat_block_hammer)",
    )
    parser.add_argument(
        "instructions",
        type=str,
        help="The instruction text for the task (e.g., 'pour water into the cup')",
    )
    parser.add_argument(
        "expert_data_num",
        type=int,
        default=50,
        help="Number of episodes to process (e.g., 50)",
    )
    parser.add_argument(
        "--load-dir",
        type=str,
        default="/data3/zjyang/real_r1/home/pine/yzj/pour/h5",
        help="Path to the directory containing H5 data files. "
             "(Default: /data3/zjyang/real_r1/home/pine/yzj/pour/h5)",
    )
    parser.add_argument(
        "--use-qpos",
        action="store_true",
        help="Use joint angles (qpos) instead of end effector pose. "
             "By default, end effector pose (ee_pose) is used.",
    )
    parser.add_argument(
        "--no-wrist",
        action="store_true",
        help="Exclude wrist camera data (cam_left_wrist and cam_right_wrist). "
             "By default, wrist cameras are included.",
    )
    args = parser.parse_args()

    task_name = args.task_name
    instructions = args.instructions
    expert_data_num = args.expert_data_num
    load_dir = args.load_dir

    # 默认使用 ee_pose（end effector pose），除非用户明确指定 --use-qpos
    use_end_pose = not args.use_qpos
    
    # 默认使用手腕相机，除非用户明确指定 --no-wrist
    use_wrist = not args.no_wrist

    begin = 0
    print(f'read data from path:{load_dir}')
    print(f'Task: {task_name}')
    print(f'Instructions: {instructions}')
    print(f'Using {"end pose (ee_pose)" if use_end_pose else "joint angles (qpos)"}')
    print(f'Wrist cameras: {"enabled" if use_wrist else "disabled"}')

    target_dir = f"processed_data/{task_name}-{expert_data_num}"
    begin = data_transform(
        load_dir,
        expert_data_num,
        target_dir,
        task_name,
        instructions,
        use_wrist=use_wrist,
    )
