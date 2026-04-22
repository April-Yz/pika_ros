# PIKA Charuco 手眼标定说明

这套流程适合你现在的使用方式：手动拖动机械臂改变夹爪/末端位置，或者手持移动 Charuco 标定板。每次采样前先停稳，确认 OpenCV 窗口里检测到了足够多 Charuco 角点，再按 `s` 保存一组样本。

## 标定板参数

脚本默认标定板参数：

- `SQUARES_X=7`
- `SQUARES_Y=5`
- `SQUARE_LENGTH=0.037`
- `MARKER_LENGTH=0.027`
- `ARUCO_DICT=cv2.aruco.DICT_5X5_100`

这里的 `SQUARES_X` 和 `SQUARES_Y` 是方格数，不是内部角点数。打印后建议用尺子重新测量方格边长和 ArUco marker 边长。如果实测值不同，运行脚本时用 `--square-length` 和 `--marker-length` 覆盖默认值。

## FK 位姿

可以把 `monitor_dual_piper_lowfreq_tmux.bash` 里的 `FK` 当机器人末端位姿使用，前提是它会随着你手动拖动机械臂而变化。

使用的话题：

- 左臂：`/piper_FK_l/urdf_end_pose_orient`
- 右臂：`/piper_FK_r/urdf_end_pose_orient`

不要用 `/pika_pose_l` 或 `/pika_pose_r` 做手眼标定。它们是定位设备位姿，不是机器人 FK。

注意：这个 FK 表示的是当前 Pika/Piper FK 节点定义的末端/TCP，不一定等于机械臂 flange。只要标定和后续使用时都采用同一个 FK 定义，结果就是一致的。

标定前建议确认 FK 会变化：

```bash
rostopic echo /piper_FK_r/urdf_end_pose_orient
```

## 启动基础系统

标定时不需要启动数据采集 s5/s6。按你的常规双臂流程启动即可。

```bash
roscore
```

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_multi_sensor_sync_capture.bash sensor
```

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_multi_gripper_sync_capture.bash gripper
```

```bash
conda activate pika
source ~/pika_ros/install/setup.zsh
roslaunch pika_remote_piper teleop_rand_multi_piper.launch
```

检查相机和 FK：

```bash
rostopic echo -n 1 /piper_FK_r/urdf_end_pose_orient
rostopic echo -n 1 /gripper/camera_r/color/camera_info
```

## 腕部相机标定

腕部相机是 eye-in-hand 标定。目标是求：

```text
gripper_T_camera
```

含义是“当前 FK 末端/TCP坐标系到腕部相机 color optical frame 的固定变换”。

链式使用方式：

```text
P_base = T_base_gripper * T_gripper_camera * P_camera
```

### 右腕部相机

把 Charuco 标定板固定在桌面或支架上，标定过程中不要移动标定板。只移动右臂，让右腕部相机从不同位置和角度看到标定板。

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name right_wrist \
  --image-topic /gripper/camera_r/color/image_raw \
  --camera-info-topic /gripper/camera_r/color/camera_info \
  --robot-pose-topic /piper_FK_r/urdf_end_pose_orient
```

输出：

```text
~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json
~/pika_ros/calibration/handeye/samples_right_wrist.npz
```

### 左腕部相机

流程和右腕部相机相同，只是换成左臂 FK 和左腕部相机话题。

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name left_wrist \
  --image-topic /gripper/camera_l/color/image_raw \
  --camera-info-topic /gripper/camera_l/color/camera_info \
  --robot-pose-topic /piper_FK_l/urdf_end_pose_orient
```

输出：

```text
~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json
~/pika_ros/calibration/handeye/samples_left_wrist.npz
```

### 窗口按键

- `s`：保存当前样本
- `q`：求解并退出
- `Esc`：不求解，直接退出

建议样本数：

- 腕部相机：`25-50` 组
- 左右腕分开标定，不要同时移动两只手

### 视角选择：正视和斜视

你观察到“尽量垂直看板子时误差变小”是合理的。大约 `45` 度或更大的斜视角容易带来更大的 `solvePnP` 位姿误差，原因包括：

- Charuco 角点在图像里更密集，像素级角点误差会被放大成更大的 3D 位姿误差。
- 斜视时远端角点更小、更容易模糊或被遮挡。
- 标定板平面 PnP 对角点分布和角点精度比较敏感，极端斜视会让姿态估计不稳定。

但也不要所有样本都完全正视、只改变平移。手眼标定需要足够的机器人旋转激励。更稳的采样策略是：

- 主要样本保持正视或轻微斜视，例如 `0-30` 度。
- 少量样本加入中等斜视，例如 `30-45` 度。
- 避免极端斜视、角点闪烁、只看到少量角点的样本。
- 每组样本仍要覆盖不同 roll/pitch/yaw，不能只平移。

如果“少量样本 + 正视”为主得到低残差，还要检查 `diagnose_handeye_samples.py` 里的 FK spread。只要 FK 旋转和平移范围足够，低残差才可信。

## 继续采样与 Resume

如果第一次采样结果还可以，但想继续追加样本，不需要从零开始。使用 `--resume-samples` 可以加载已有 `.npz` 样本，然后把新按 `s` 保存的样本追加进去，最后按 `q` 重新求解并输出新结果。

### Resume 原理

`.npz` 文件里保存的是每个样本的两类 4x4 位姿矩阵：

- `base_T_gripper`：采样时的机器人 FK 末端位姿
- `camera_T_board`：相机看到的 Charuco 标定板位姿

`--resume-samples old_samples.npz` 会先把旧样本全部加载到内存中。之后你继续移动机械臂并按 `s`，新样本会追加到旧样本后面。按 `q` 后，脚本会用“旧样本 + 新样本”整体重新求解外参。

注意：

- `--resume-samples` 不会修改原始旧 `.npz` 文件。
- 新输出文件名由 `--name` 决定。
- 如果 `--name` 和旧结果同名，会覆盖同名 JSON/NPZ。
- 如果旧样本本身是坏的，例如 FK 恒定，不要 resume 它，应先移走或换一个干净样本文件。
- Resume 追加时，脚本会检查连续样本的 FK 变化。如果 FK 变化太小，会拒绝保存，避免再次采到无效样本。

### 右手继续采样

基于已有正式右手样本继续追加，并覆盖正式右手结果：

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name right_wrist \
  --resume-samples ~/pika_ros/calibration/handeye/samples_right_wrist.npz \
  --image-topic /gripper/camera_r/color/image_raw \
  --camera-info-topic /gripper/camera_r/color/camera_info \
  --robot-pose-topic /piper_FK_r/urdf_end_pose_orient
```

如果只想做实验，不覆盖正式结果：

```bash
/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name right_wrist_refined \
  --resume-samples ~/pika_ros/calibration/handeye/samples_right_wrist.npz \
  --image-topic /gripper/camera_r/color/image_raw \
  --camera-info-topic /gripper/camera_r/color/camera_info \
  --robot-pose-topic /piper_FK_r/urdf_end_pose_orient
```

### 左手继续采样

基于已有正式左手样本继续追加，并覆盖正式左手结果：

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name left_wrist \
  --resume-samples ~/pika_ros/calibration/handeye/samples_left_wrist.npz \
  --image-topic /gripper/camera_l/color/image_raw \
  --camera-info-topic /gripper/camera_l/color/camera_info \
  --robot-pose-topic /piper_FK_l/urdf_end_pose_orient
```

如果只想做实验，不覆盖正式结果：

```bash
/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_in_hand \
  --name left_wrist_refined \
  --resume-samples ~/pika_ros/calibration/handeye/samples_left_wrist.npz \
  --image-topic /gripper/camera_l/color/image_raw \
  --camera-info-topic /gripper/camera_l/color/camera_info \
  --robot-pose-topic /piper_FK_l/urdf_end_pose_orient
```

## Head D435 标定方案

Head D435 是固定在机器人外部/头部的相机，属于 eye-to-hand。这里有两种方案。

### 方案 A：标定板固定到末端

这是传统 eye-to-hand 方法。把 Charuco 标定板刚性固定到一只夹爪/末端上，D435 保持不动。移动机械臂，让 D435 从不同位置和角度看到标定板。

如果 D435 还没有启动，先启动：

```bash
roslaunch realsense2_camera rs_camera.launch \
  serial_no:=817412070803 \
  camera:=camera \
  tf_prefix:=camera \
  enable_color:=true \
  enable_depth:=false \
  enable_pointcloud:=false
```

用右臂夹持标定板：

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_to_hand \
  --name head_d435_right_base \
  --image-topic /camera/color/image_raw \
  --camera-info-topic /camera/color/camera_info \
  --robot-pose-topic /piper_FK_r/urdf_end_pose_orient
```

用左臂夹持标定板：

```bash
/usr/bin/python3 ~/pika_ros/scripts/pika_charuco_handeye_calib.py \
  --mode eye_to_hand \
  --name head_d435_left_base \
  --image-topic /camera/color/image_raw \
  --camera-info-topic /camera/color/camera_info \
  --robot-pose-topic /piper_FK_l/urdf_end_pose_orient
```

结果里使用：

```text
base_T_camera
```

它相对于参与标定那只机械臂 base。用右臂标定得到 `right_base -> D435`，用左臂标定得到 `left_base -> D435`。

### 方案 B：移动标定板，腕部相机辅助标定 Head D435

如果 D435 很难看到固定在末端上的标定板，可以使用这个方案。标定板可以手持移动，D435 和至少一个腕部相机同时看到同一块标定板即可。

这个方案依赖已经完成的左右腕部相机外参：

```text
~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json
~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json
```

它还会使用左右腕部标定时的样本，粗略估计左右 base 的相对关系：

```text
~/pika_ros/calibration/handeye/samples_left_wrist.npz
~/pika_ros/calibration/handeye/samples_right_wrist.npz
```

标定原理：

```text
腕部相机观测 + 腕部外参 + FK -> left_base_T_board
Head D435 观测 -> head_camera_T_board
left_base_T_head = left_base_T_board * inverse(head_camera_T_board)
```

如果右腕部相机参与观测，会先通过估计出的 `left_base_T_right_base` 把右 base 下的 board 位姿转换到 left base 下。最终输出统一是：

```text
left_base_T_head_camera
```

运行前启动 D435：

```bash
roslaunch realsense2_camera rs_camera.launch \
  serial_no:=817412070803 \
  camera:=camera \
  tf_prefix:=camera \
  enable_color:=true \
  enable_depth:=false \
  enable_pointcloud:=false
```

运行标定：

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_calibrate_head_from_wrist_boards.py \
  --name head_d435
```

窗口会显示左腕、右腕、head 三个画面。如果某一路没有图像或没有 camera info，窗口里会直接显示缺失的话题名。

### 使用 try2 腕部结果标定 Head D435

如果你认为 try2 的左右腕结果更好，可以显式传入 try2 的左右腕外参、样本和 try2 的左右 base 关系：

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

/usr/bin/python3 ~/pika_ros/scripts/pika_calibrate_head_from_wrist_boards.py \
  --name head_d435_try2 \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_try2_eye_in_hand.json \
  --left-samples ~/pika_ros/calibration/handeye/samples_left_wrist_try2.npz \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_try2_eye_in_hand.json \
  --right-samples ~/pika_ros/calibration/handeye/samples_right_wrist_try2.npz \
  --left-base-T-right-base ~/pika_ros/calibration/handeye/left_base_T_right_base_try2.json \
  --left-image-topic /gripper/camera_l/color/image_raw \
  --left-info-topic /gripper/camera_l/color/camera_info \
  --right-image-topic /gripper/camera_r/color/image_raw \
  --right-info-topic /gripper/camera_r/color/camera_info \
  --head-image-topic /camera/color/image_raw \
  --head-info-topic /camera/color/camera_info \
  --left-fk-topic /piper_FK_l/urdf_end_pose_orient \
  --right-fk-topic /piper_FK_r/urdf_end_pose_orient
```

其中 `--left-base-T-right-base` 是可选但推荐的。如果不传，脚本会根据 `--left-samples`、`--right-samples` 和左右腕外参现场估计一次左右 base 关系。已经有 `left_base_T_right_base_try2.json` 时，显式传入可以避免每次重复估计，也避免混用默认正式结果。

### 如果 Head D435 由 s5 启动

脚本不关心 D435 是单独 `roslaunch realsense2_camera` 启动，还是由 s5 启动。关键是 ROS 话题名。

先查实际话题：

```bash
rostopic list | grep -E 'camera|D435|d435|head|buffered_capture'
```

再确认类型：

```bash
rostopic type /camera/color/image_raw
rostopic type /camera/color/camera_info
```

如果 s5 启动后 D435 原始话题仍是：

```text
/camera/color/image_raw
/camera/color/camera_info
```

就不用改参数。

如果你的 s5 只提供了别的 head cam 话题，例如：

```text
/some_ns/color/image_raw
/some_ns/color/camera_info
```

就把它们传给：

```text
--head-image-topic
--head-info-topic
```

例如：

```bash
/usr/bin/python3 ~/pika_ros/scripts/pika_calibrate_head_from_wrist_boards.py \
  --name head_d435_s5 \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_try2_eye_in_hand.json \
  --left-samples ~/pika_ros/calibration/handeye/samples_left_wrist_try2.npz \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_try2_eye_in_hand.json \
  --right-samples ~/pika_ros/calibration/handeye/samples_right_wrist_try2.npz \
  --left-base-T-right-base ~/pika_ros/calibration/handeye/left_base_T_right_base_try2.json \
  --head-image-topic /camera/color/image_raw \
  --head-info-topic /camera/color/camera_info
```

不要把 `/buffered_capture/...` 话题当作首选标定输入，除非确认它正在发布原始或低延迟图像和对应 camera_info。标定更推荐直接订阅相机原始 topic。

按键：

- `s`：保存当前样本
- `q`：求解并退出
- `Esc`：不求解，直接退出

采样要求：

- 标定板可以手持移动。
- 每次按 `s` 时，D435 必须看到标定板。
- 至少一个腕部相机必须同时看到标定板。
- 最好 D435、左腕、右腕三者都同时看到标定板。
- 采 `20-40` 组，覆盖不同位置、距离和角度。
- 按 `s` 前停稳标定板，避免运动模糊。

输出：

```text
~/pika_ros/calibration/handeye/head_d435_head_from_wrist.json
~/pika_ros/calibration/handeye/samples_head_d435_head_from_wrist.npz
```

结果里使用：

```text
left_base_T_head_camera
```

使用方式：

```text
P_left_base = left_base_T_head_camera * P_head_camera
```

注意：

- 这个方法是间接标定，精度会叠加左右腕外参、左右 base 关系、FK 和 Charuco 检测误差。
- 它适合先得到可用的 head cam 外参。
- 如果要高精度，应后续做重投影/TF 验证，必要时做离群样本剔除。
- OpenCV 的 `drawFrameAxes Some of projected axes endpoints are out of frame` 通常不是致命错误，只表示画出来的坐标轴端点超出画面。只要角点检测稳定且能保存样本，可以继续。

## 左右 Base 转换关系

如果左右腕部相机都完成了标定，并且它们标定时看到的是同一块固定不动的 Charuco 板，可以离线估计左右 base 的相对关系。

计算逻辑：

```text
left_base_T_board = left_base_T_left_gripper * left_gripper_T_left_camera * left_camera_T_board
right_base_T_board = right_base_T_right_gripper * right_gripper_T_right_camera * right_camera_T_board

left_base_T_right_base = left_base_T_board * inverse(right_base_T_board)
```

脚本：

```text
~/pika_ros/scripts/estimate_dual_base_transform.py
```

### 使用正式左右腕结果计算

```bash
/usr/bin/python3 ~/pika_ros/scripts/estimate_dual_base_transform.py \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json \
  --left-samples ~/pika_ros/calibration/handeye/samples_left_wrist.npz \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json \
  --right-samples ~/pika_ros/calibration/handeye/samples_right_wrist.npz \
  --output ~/pika_ros/calibration/handeye/left_base_T_right_base.json
```

### 使用 try2 左右腕结果计算

```bash
/usr/bin/python3 ~/pika_ros/scripts/estimate_dual_base_transform.py \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_try2_eye_in_hand.json \
  --left-samples ~/pika_ros/calibration/handeye/samples_left_wrist_try2.npz \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_try2_eye_in_hand.json \
  --right-samples ~/pika_ros/calibration/handeye/samples_right_wrist_try2.npz \
  --output ~/pika_ros/calibration/handeye/left_base_T_right_base_try2.json
```

输出里的关键字段：

```text
left_base_T_right_base
```

含义是：

```text
right_base 坐标 -> left_base 坐标
```

如果后续有一个点在右臂 base 坐标下：

```text
P_left_base = left_base_T_right_base * P_right_base
```

### Base 转换结果的可信度

这个方法是间接估计，会叠加：

- 左腕手眼误差
- 右腕手眼误差
- 两边 Charuco 检测误差
- 两边 FK 误差

因此它适合作为左右 base 的粗对齐或初值。如果要作为高精度双臂 base 标定，建议专门采更多共同标定板数据，并做离群样本剔除。

判断输出质量时优先看：

- `left_board_spread.translation_mean_m`
- `right_board_spread.translation_mean_m`
- `left_board_spread.rotation_mean_deg`
- `right_board_spread.rotation_mean_deg`

这些数越小，说明固定标定板在对应 base 下越稳定。一般平均平移在 `5-10 mm` 量级比较好，超过 `20-30 mm` 需要谨慎使用。

## 标定板是否必须完整可见

严格来说，Charuco 不要求整张 `7x5` 标定板每次都完整可见。只要检测到足够多的 Charuco 角点，脚本就能用 `solvePnP` 求出当前相机到标定板的位姿。

实际建议：

- 推荐采样：尽量让整张板完整出现在画面内，尤其是标定初期和大部分样本。
- 可接受采样：可以有少量边缘样本只看到部分标定板，但应至少检测到 `8` 个以上 Charuco 角点，且角点分布不能挤在一小块区域。
- 不建议采样：只看到一两个 ArUco marker、角点集中在画面一角、标定板严重倾斜、边缘被遮挡很多、检测结果闪烁不稳定。

脚本默认 `--min-corners 8`。少于 8 个 Charuco 角点时不会保存有效检测。为了质量，实际按 `s` 前建议看窗口里的 `corners=`，优先保存 `12-24` 个角点以上的样本。

你的 `7x5` 方格 Charuco 板内部角点数量通常是 `(7-1) * (5-1) = 24` 个。能看到 20 个以上通常比较稳；8-12 个只适合作为少量补充视角，不建议成为主要样本。

## 采样注意事项

- 每次按 `s` 前，先让机械臂或标定板完全停稳。
- 标定板和相机之间不要有运动模糊。
- 腕部相机 eye-in-hand 标定时，标定板必须固定不动。
- 方案 A 的 D435 eye-to-hand 标定时，标定板必须刚性固定在夹爪/末端上，不能手持。
- 方案 B 的移动标定板标定 head cam 时，标定板可以手持，但按 `s` 时必须停稳。
- 采样时要改变姿态，不能只做平移。
- 让标定板覆盖画面中心、左上、右上、左下、右下、上边、下边等区域。
- 距离不要太近导致标定板出画，也不要太远导致角点太小。
- 避免极端斜视角，角点检测会不稳定。
- 避免强反光、暗光、阴影和运动模糊。
- 如果 `corners=` 数字跳动很大，先改善光照、距离或相机曝光，再采样。
- 如果结果残差很大，优先检查标定板尺寸、相机话题、FK 话题、左右臂是否混用。

## 结果质量判断

脚本求解后会打印残差。

腕部相机建议目标：

- `translation_mean_m`：理想情况低于 `0.01-0.02`
- `rotation_mean_deg`：理想情况低于 `2-3` 度

Head cam 方案 B 是间接标定，残差可能略大。若平移误差明显超过几厘米，通常说明采样或配置有问题。

常见问题：

- `translation_mean_m` 很大：标定板尺寸填错、FK 话题错、标定板移动了、保存样本时还在动。
- `rotation_mean_deg` 很大：姿态变化不足、角点检测不稳定、相机 optical frame 或左右相机话题混用。
- 样本数量够但结果不稳定：采样姿态太集中，缺少 roll/pitch/yaw 变化。
- 采集后结果是单位矩阵：通常是 FK 没变化，旧坏样本可以用 `diagnose_handeye_samples.py` 检查。

## 离线诊断

检查已有腕部样本：

```bash
/usr/bin/python3 ~/pika_ros/scripts/diagnose_handeye_samples.py \
  ~/pika_ros/calibration/handeye/samples_right_wrist.npz
```

如果看到 `robot FK spread` 接近 0，说明这些样本不能用于手眼标定。
