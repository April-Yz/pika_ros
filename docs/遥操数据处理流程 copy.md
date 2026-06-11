# 遥操数据处理流程

本文档记录当前 `pika_ros` 遥操采集数据到 RobotWin 训练数据的处理流程。

示例任务：

- task name: `pnp_bread`
- instruction: `Pick up two breads, then place them onto the blue plate.`
- 原始数据目录：`/home/piper/agilex/pnp_bread`

## 0. 环境

建议使用系统 Python 跑和 OpenCV 相关的脚本：

```bash
/usr/bin/python3
```

如果使用 conda，环境至少需要：

```bash
conda create -n robotwin-data python=3.10 -y
conda activate robotwin-data
conda install -c conda-forge numpy h5py opencv scipy pyyaml -y
```

## 1. 生成视频预览

先为每个 episode 生成三视角拼接视频：

```bash
# /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py \
#   --task-name pnp_bread \
#   --overwrite

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py \
    --task-name stack_cup \
    --episode-subdir unprocessed \
    --overwrite

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py \
    --task-name place_bread_basket \
    --episode-subdir unprocessed \
    --overwrite

```

每个 episode 下会生成：

```bash
camera_overview.mp4
```

## 2. 频率可视化

查看整个任务目录的采集频率：

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py \
  --task-name pnp_bread

/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py \
  --task-name stack_cup 

/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py \
  --task-name stack_cup 

```

查看单个 episode：

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py \
  --task-name pnp_bread \
  30
```

查看多个 episode：

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py \
  --task-name pnp_bread \
  30 31 32
```

## 3. 自动筛选

自动筛选会把原始根目录下的 `episode*` 移动到：

- `/home/piper/agilex/pnp_bread/good/episodeX`
- `/home/piper/agilex/pnp_bread/bad/episodeX`

筛选规则：

- 缺少三路 RGB 视角则进入 `bad`
- 缺少 state/action 所需的 puppet pose 或 gripper 数据则进入 `bad`
- 缺少 `camera_overview.mp4` 则进入 `bad`
- 三路 RGB 最低频率低于 `8 Hz` 则进入 `bad`
- 三路 RGB 最低频率在 `[8, 10)` 会进入 `good`，但终端黄色提示并记录日志

默认使用 robot gripper 检查：

```bash
/usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py auto-split \
  --task-name pnp_bread


```

如果最终处理使用 sensor gripper，自动筛选时也建议检查 sensor gripper 是否存在：

```bash
/usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py auto-split \
  --task-name pnp_bread \
  --gripper-source sensor

/usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py auto-split \
  --task-name stack_cup \
  --gripper-source sensor
```

日志位置：

```bash
/home/piper/agilex/pnp_bread/curation_log.jsonl
```

注意：

- 该步骤会移动目录。
- 如果已经存在 `good/episodeX` 或 `bad/episodeX`，默认不会覆盖。
- 确认要覆盖时再加 `--overwrite-existing`。

## 4. 人工视频筛选

自动筛选后，对 `good/` 里的 episode 顺序播放 `camera_overview.mp4`：

```bash
/usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py manual-review \
  --task-name pnp_bread

/usr/bin/python3 ~/pika_ros/scripts/curate_teleop_episodes.py manual-review \
  --task-name stack_cup
```

播放窗口快捷键：

- `g`：标记为好，保留在 `good`
- `m`：标记为中等质量，移动到 `medium`
- `n`：下一个，等价于保留
- `b`：标记为坏，移动到 `bad`
- `p`：上一个
- `r`：重播当前视频
- `space`：暂停/继续
- `q`：退出人工筛选

说明：

- `medium` 默认和 `bad` 一样，不参与后续 HDF5 处理。
- 这样可以把“明显坏数据”和“边缘质量数据”分开保留。

日志位置：

```bash
/home/piper/agilex/pnp_bread/manual_curation_log.jsonl
```

## 5. 静止帧裁剪

对人工筛选后的 `good` 数据进行静止帧裁剪，输出到新目录，不覆盖原始数据：

```bash
# /usr/bin/python3 ~/pika_ros/scripts/trim_static_teleop_frames.py \
#   /home/piper/agilex/pnp_bread/good \
#   --output-dir /home/piper/agilex/pnp_bread/good_trimmed_01mm \
#   --motion-threshold 0.0001 \
#   --gripper-source sensor

/usr/bin/python3 ~/pika_ros/scripts/trim_static_teleop_frames.py \
  /home/piper/agilex/stack_cup/good \
  --output-dir /home/piper/agilex/stack_cup/good_trimmed_01mm \
  --motion-threshold 0.0001 \
  --gripper-source sensor
```

如果你想单独检查某个 `episode` 为什么有帧被删除，可以直接看“被删帧”和“上一保留帧 / 上一原始帧”的 7 维差值：

```bash
/usr/bin/python3 ~/pika_ros/scripts/inspect_trim_static_episode.py \
  /home/piper/agilex/pnp_bread/good/episode147 \
  --motion-threshold 0.0001 \
  --gripper-source sensor \
  --limit 30 \
  --output-json /home/piper/agilex/pnp_bread/debug_trim/episode147_inspection.json
```

这个检查脚本会输出：

- 每个被删帧相对“上一保留帧”的左右手 7 维绝对变化量之和
- 每个被删帧相对“上一原始帧”的左右手 7 维绝对变化量之和
- 每一维的详细差值：
  - `x, y, z, roll, pitch, yaw, gripper_distance`

这样你可以区分：

- 机器人确实几乎没动
- 机器人在连续微动，但累计到上一保留帧的变化仍然低于阈值
- 某个维度的单位或权重让阈值判断不符合直觉

规则：

- 基于头部相机时间线对齐数据
- 每帧构造左右手各 7 维：
  - `x, y, z, roll, pitch, yaw, gripper_distance`
- 左右手分别计算 7 维绝对变化量之和：
  - `abs(dx) + abs(dy) + abs(dz) + abs(droll) + abs(dpitch) + abs(dyaw) + abs(dgripper)`
- 如果某一帧相对上一个保留帧的左右手最大“7维绝对变化量之和”小于阈值，则删除
- 第一帧和最后一帧始终保留

关于旋转量：

- `roll, pitch, yaw` 直接读取原始 `endPose` JSON 中的值
- 单位是 `rad`
- 当前脚本不会把旋转量换算成米，也不会做额外归一化
- 也就是说，当前位置变化 `m`、旋转变化 `rad`、夹爪变化量会直接一起参与上面的求和阈值
- 因此 `--motion-threshold` 目前是一个工程上的混合阈值，不是严格物理同量纲的距离
- 如果后面你觉得旋转量权重过大或过小，再单独给旋转项加系数会更稳

输出报告：

```bash
/home/piper/agilex/pnp_bread/good_trimmed_1mm/static_trim_report.json
```

报告中包含每个 episode：

- 原始帧数
- 剩余帧数
- 删除帧数
- 剩余百分比
- 输出目录

## 6. 转换为 RobotWin HDF5

处理人工筛选后的 good 数据：

Stack the dark red and light red cups onto the green cup.

```bash
/usr/bin/python3 ~/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_bread \
  "Pick up two breads, then place them onto the blue plate." \
  147 \
  --episode-subdir good \
  --gripper-source sensor \
  --output-dir /home/piper/agilex/processed_robotwin/pnp_bread-good-147-sensor
```

处理静止帧裁剪后的数据：

```bash
/usr/bin/python3 ~/pika_ros/scripts/process_data_robotwin_headcam.py \
  /home/piper/agilex/pnp_bread \
  "Pick up two breads, then place them onto the blue plate." \
  147 \
  --episode-subdir good_trimmed_01mm \
  --gripper-source sensor \
  --output-dir /home/piper/agilex/processed_robotwin/pnp_bread-good-trimmed-01mm-147-sensor

  python ~/pika_ros/scripts/process_data_robotwin_headcam.py \
    /home/piper/agilex/pnp_bread \
    "Pick up two breads, then place them onto the blue plate." \
    147 \
    --episode-subdir good_trimmed_01mm \
    --gripper-source sensor \
    --output-dir /home/piper/agilex/processed_robotwin/pnp_bread-good-trimmed-01mm-147-sensor

```

说明：

- `--episode-subdir good` 表示从 `/home/piper/agilex/pnp_bread/good/episode*` 读取。
- `--episode-subdir good_trimmed_1mm` 表示从裁剪后的目录读取。
- `--gripper-source sensor` 表示 state/action 中的 gripper 使用 `pikaSensor_l/r`。

## 7. 检查处理后的 HDF5

检查一个处理后的 episode：

```bash
/usr/bin/python3 ~/pika_ros/scripts/check_processed_robotwin_headcam.py \
  /home/piper/agilex/processed_robotwin/pnp_bread-good-trimmed-1mm-147-sensor \
  --episode 0
```

导出图片预览：

```bash
/usr/bin/python3 ~/pika_ros/scripts/export_robotwin_hdf5_preview_images.py \
  /home/piper/agilex/processed_robotwin/pnp_bread-good-trimmed-1mm-147-sensor/episode_0/episode_0.hdf5
```

默认预览输出：

```bash
/home/piper/agilex/robotwin_hdf5_previews/pnp_bread-good-trimmed-1mm-147-sensor/episode_0
```

是的，这条命令用的是 sensor 数据。关键就在这里：

  --gripper-source sensor

  这会让 [process_data_robotwin_headcam.py](/home/piper/pika_ros/scripts/
  process_data_robotwin_headcam.py) 读取：

  - gripper/encoder/pikaSensor_l
  - gripper/encoder/pikaSensor_r

  而不是：

  - gripper/encoder/pikaGripper_l
  - gripper/encoder/pikaGripper_r

  我给你补了一个统计脚本：pika_ros/scripts/summarize_teleop_state_ranges.py

  你可以直接看 good_trimmed_01mm 里每个 episode、每个维度的取值范围：

  python ~/pika_ros/scripts/summarize_teleop_state_ranges.py \
    /home/piper/agilex/pnp_bread \
    --episode-subdir good_trimmed_01mm \
    --gripper-source sensor \
    --output-json /home/piper/agilex/pnp_bread/debug_ranges/
  good_trimmed_01mm_sensor_ranges.json

  它会输出每个 episode 的 14 维范围：

  - left_x/y/z/roll/pitch/yaw/gripper
  - right_x/y/z/roll/pitch/yaw/gripper

  如果你只想先快速看左右 gripper 的范围，用精简模式：

  python ~/pika_ros/scripts/summarize_teleop_state_ranges.py \
    /home/piper/agilex/pnp_bread \
    --episode-subdir good_trimmed_01mm \
    --gripper-source sensor \
    --compact

  如果你只看几个 episode，比如 147 和 149：

  python ~/pika_ros/scripts/summarize_teleop_state_ranges.py \
    /home/piper/agilex/pnp_bread