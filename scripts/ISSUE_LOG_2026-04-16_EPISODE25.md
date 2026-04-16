# Issue Log: 2026-04-16 Episode25

## 问题概述

用户体感上从脚踏板开始到结束持续了较长时间，但最终导出的视频只包含中间一小段。

相关 episode：

```text
/home/piper/agilex/data/episode25
```

## 结论

问题不在视频渲染脚本，而在采集阶段：

- `s6` 正常收到了脚踏板开始/结束指令
- `s5` 也正常创建了 `episode25`
- 但 `s5` 在录制开始约 3 秒后，因为多路 topic 频率检查失败，提前自动停止了采集

因此最终视频只覆盖到采集器实际存活的那一小段。

## 关键时间线

### 脚踏板日志

来自：

```text
$HOME/agilex/data/foot_pedal_capture.log
```

关键记录：

```text
2026-04-16T16:11:11.041489  pedal_start_request  episode25
2026-04-16T16:11:12.449855  capture_started      episode25
2026-04-16T16:11:58.208977  pedal_stop_request
2026-04-16T16:11:59.116524  capture_stopped
```

说明：

- 用户的开始/结束踏板动作被正常接收
- 从 `s6` 的角度看，采集窗口大约持续了 46 秒

### 采集服务日志

来自：

```text
$HOME/agilex/data/capture_service.log
```

与 `episode25` 相关的关键记录：

```text
service_start_new             episodeDir=/home/piper/agilex/data/episode25
service_toggle_stop_existing  episodeDir=/home/piper/agilex/data/episode25
```

说明：

- `episode25` 确实被创建并启动
- 但后续被采集器自己提前终止

### episode 内部采集时间

来自：

```text
$HOME/agilex/data/episode25/capture_timing.log
```

关键记录：

```text
capture_object_created
capture_shutdown_begin
capture_shutdown_done
```

以及帧摘要：

```text
camera/color/pikaGripperDepthCamera_l  start=0            last=0            count=0
camera/color/pikaGripperDepthCamera_r  start=177632707... last=177632710... count=124
camera/color/pikaGripperFisheyeCamera_l start=177632707... last=177632710... count=126
camera/color/pikaGripperFisheyeCamera_r start=177632707... last=177632710... count=21
camera/color/myD435                     start=177632707... last=177632710... count=107
camera/depth/pikaGripperDepthCamera_l   start=0            last=0            count=0
camera/depth/pikaGripperDepthCamera_r   start=177632707... last=177632710... count=122
```

说明：

- 左侧 gripper depth 相机两路完全没有数据
- 右侧 fisheye 虽然有数据，但帧率明显偏低
- 多数有效图像数据只持续了约 3 秒

## 直接触发提前停止的原因

来自 `s5` 输出和 `episode25/statistic.txt`：

```text
/gripper/camera_l/color/image_raw: 0 / 0(-nanhz)
Check the frequency of /gripper/camera_l/color/image_raw

/gripper/camera_l/aligned_depth_to_color/image_raw: 0 / 0(-nanhz)
Check the frequency of /gripper/camera_l/aligned_depth_to_color/image_raw

/gripper/camera_fisheye_r/color/image_raw: 21 5.18499hz
Check the frequency of /gripper/camera_fisheye_r/color/image_raw

The device frequency does not match, stop, waiting for the end signal.
```

说明：

- 左侧 gripper depth 彩色流缺失
- 左侧 gripper depth 深度流缺失
- 右侧 fisheye 频率远低于当前阈值
- `data_tools_dataCapture` 因频率检查失败而主动停止

## 为什么用户感觉录制持续了更久

因为：

- `s6` 只记录“脚踏板何时请求开始/结束”
- `s5` 才真正决定“采集是否继续”

这次 `s6` 在大约 46 秒后才收到停止操作，但 `s5` 在开始后约 3 秒就已经由于频率检查失败而提前结束了实际采集。

所以：

- 用户感知的操作时长：长
- 真正落盘的视频时长：短

## 对应视频渲染结果

命令：

```bash
/usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 25
```

输出摘要：

```text
color/myD435: 82 frames
color/pikaGripperDepthCamera_r: 94 frames
color/pikaGripperFisheyeCamera_l: 96 frames
color/pikaGripperFisheyeCamera_r: 16 frames
```

这与约 3 秒左右的实际采集窗口一致。

## 本次新增的辅助日志

为后续继续定位类似问题，当前代码已新增：

- `datasetDir/foot_pedal_capture.log`
- `datasetDir/capture_service.log`
- `episodeN/capture_timing.log`

用于分别记录：

- 脚踏板按下时间
- 服务层开始/结束时间
- episode 内部真实首帧/末帧时间
