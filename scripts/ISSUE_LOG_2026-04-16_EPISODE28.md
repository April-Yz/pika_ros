# Episode28 录制一致性与频率分析

日期：2026-04-16

## 结论

- `episode28` 的实际录制时长与脚踏板开始/结束时间基本一致
- 这次没有出现夹爪双击与脚踏板互相干扰的迹象
- 采集期间 `s5` 没有中途被其他 caller 切换
- 主要的频率特征是：
  - 左右 gripper 彩色基本在 `29-30 Hz`
  - 左右 gripper 深度基本在 `27-29 Hz`
  - D435 彩色大约 `24-25 Hz`
  - 右 fisheye 只有 `~5 Hz`
  - 左 fisheye 全程没有数据

## 时间线

### 脚踏板日志

来源：`$HOME/agilex/data/foot_pedal_capture.log`

- `18:00:47.999233` `pedal_key_down KEY_C`
- `18:00:48.001730` `pedal_start_request episode28`
- `18:00:49.197596` `capture_started episode28`
- `18:01:29.972672` `pedal_key_down KEY_C`
- `18:01:29.976359` `pedal_stop_request`
- `18:01:30.211069` `capture_stopped`

### 采集服务调用源日志

来源：`$HOME/agilex/data/capture_service_requests.log`

本次 `episode28` 只出现了脚踏板 caller：

- `callerid=/foot_pedal_capture_toggle_994183_1776333633207 start=1 end=0 episode_index=28`
- `callerid=/foot_pedal_capture_toggle_994183_1776333633207 start=0 end=1 episode_index=-1`

没有出现：

- `/sensor_serial_gripper_imu_l`
- `/sensor_serial_gripper_imu_r`

对 `episode28` 的中途 toggle 调用。

### 采集对象时间

来源：`$HOME/agilex/data/episode28/capture_timing.log`

- `18:00:48` `capture_object_created`
- `18:01:30` `capture_shutdown_begin`
- `18:01:30` `capture_shutdown_done`

这和脚踏板日志是对齐的。

## 实际录制结果

来源：`$HOME/agilex/data/episode28/statistic.txt`

- 总时长：`41.0051`

相机统计：

- `camera/color/pikaGripperDepthCamera_l 1226 29.4635`
- `camera/color/pikaGripperDepthCamera_r 1249 30.016`
- `camera/color/pikaGripperFisheyeCamera_l 0 -nan`
- `camera/color/pikaGripperFisheyeCamera_r 205 4.95709`
- `camera/color/myD435 1035 24.8252`
- `camera/depth/pikaGripperDepthCamera_l 1149 27.613`
- `camera/depth/pikaGripperDepthCamera_r 1190 28.5752`

实际磁盘文件数：

- `camera/color/myD435`: `1012`
- `camera/color/pikaGripperDepthCamera_l`: `1197`
- `camera/color/pikaGripperDepthCamera_r`: `1220`
- `camera/color/pikaGripperFisheyeCamera_r`: `201`
- `camera/depth/pikaGripperDepthCamera_l`: `1120`
- `camera/depth/pikaGripperDepthCamera_r`: `1161`

## 采集期间 hz 统计

来源：`$HOME/agilex/data/capture_status_hz.log`

统计窗口：

- `1776333648.0` 到 `1776333690.3`
- 对应 `18:00:48` 到 `18:01:30`
- 共命中 `44` 条 status 记录

### 重点 topic 平均频率

- `/gripper/camera_l/color/image_raw`
  - 平均 `29.600 Hz`
  - 范围 `29.107 ~ 31.147 Hz`
- `/gripper/camera_r/color/image_raw`
  - 平均 `30.097 Hz`
  - 范围 `30.016 ~ 31.144 Hz`
- `/gripper/camera_l/aligned_depth_to_color/image_raw`
  - 平均 `27.677 Hz`
  - 范围 `26.674 ~ 31.147 Hz`
- `/gripper/camera_r/aligned_depth_to_color/image_raw`
  - 平均 `29.065 Hz`
  - 范围 `27.787 ~ 31.144 Hz`
- `/camera/color/image_raw`
  - 平均 `24.840 Hz`
  - 范围 `24.323 ~ 28.812 Hz`
- `/gripper/camera_fisheye_r/color/image_raw`
  - 平均 `5.054 Hz`
  - 范围 `4.957 ~ 6.567 Hz`
- `/gripper/camera_fisheye_l/color/image_raw`
  - 全程无有效频率，始终 `NaN`

### 控制与状态 topic 平均频率

- `/joint_states_gripper_l`
  - 平均 `43.786 Hz`
  - 范围 `35.162 ~ 50.142 Hz`
- `/joint_states_gripper_r`
  - 平均 `47.330 Hz`
  - 范围 `46.887 ~ 51.924 Hz`
- `/piper_IK_l/receive_end_pose_orient`
  - 平均 `43.206 Hz`
  - 范围 `34.642 ~ 50.116 Hz`
- `/piper_IK_r/receive_end_pose_orient`
  - 平均 `46.487 Hz`
  - 范围 `45.989 ~ 50.408 Hz`
- `/pika_pose_l`
  - 平均 `120.063 Hz`
  - 范围 `119.942 ~ 121.290 Hz`
- `/pika_pose_r`
  - 平均 `120.063 Hz`
  - 范围 `119.942 ~ 121.290 Hz`
- `/sensor/gripper_l/data`
  - 平均 `124.388 Hz`
  - 范围 `123.579 ~ 126.967 Hz`
- `/sensor/gripper_r/data`
  - 平均 `124.956 Hz`
  - 范围 `124.753 ~ 127.024 Hz`

## 补充观察

- `masterLeft/masterRight` 在 `statistic.txt` 中存在，但本次只按你的要求分析 `s5/s6`
- 左手遥操是否启动异常不影响这次关于采集开始/结束一致性的判断
- 从采集控制层看，`episode28` 是目前最干净的一次：没有中途被别的 caller 切断

## 结论摘要

1. `episode28` 的录制窗口与脚踏板开始/结束是对齐的
2. 本次没有出现脚踏板与夹爪双击互相干扰
3. 采集期间的主要问题不在 service 冲突，而在个别输入源本身：
   - 左 fisheye 无数据
   - 右 fisheye 仅约 `5 Hz`
   - D435 彩色稳定在 `24-25 Hz` 左右，不是 30 Hz
