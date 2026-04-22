# Episode26 录制过短排查

日期：2026-04-16

## 现象

- 脚踏板开始后，用户操作持续约 45 秒
- `episode26` 实际只保存了约 6 秒数据
- `s6` 结束时提示 stop 失败，连接不到采集服务

## 时间线

### s6 脚踏板日志

来源：`$HOME/agilex/data/foot_pedal_capture.log`

- `16:57:24` `foot_pedal_ready device=/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd next_episode=episode26`
- `16:57:28.222071` `pedal_key_down KEY_C`
- `16:57:28.223770` `pedal_start_request episode26`
- `16:57:29.834788` `capture_started episode26`
- `16:58:14.502936` `pedal_stop_request`

### s5 采集服务日志

来源：`$HOME/agilex/data/capture_service.log`

- `16:57:28` `service_start_new episodeDir=/home/piper/agilex/data/episode26`
- `16:57:35` `service_toggle_stop_existing episodeDir=/home/piper/agilex/data/episode26`
- `16:57:37` `service_toggle_start_new episodeDir=/home/piper/agilex/data/episode0`

### s5 tmux 输出

来源：`tmux capture-pane -pt s5`

- `data_tools_dataCapture-3 process has died ... exit code -11`
- `restarting process`
- `----> data capture Started.`

### s6 tmux 输出

来源：`tmux capture-pane -pt s6`

- `Right pedal pressed. Requesting capture start for episode26.`
- `Capture started successfully: episode26`
- `Right pedal pressed. Requesting capture stop.`
- `Capture stop failed: unable to connect to service: [Errno 111] Connection refused`

## 目录内实际结果

来源：`$HOME/agilex/data/episode26`

`statistic.txt`：

- 总时长：`6.00505`
- `camera/color/pikaGripperDepthCamera_l 207 30.1378`
- `camera/color/pikaGripperDepthCamera_r 203 30.1406`
- `camera/color/myD435 186 27.3737`
- `camera/depth/pikaGripperDepthCamera_l 204 30.1399`
- `camera/depth/pikaGripperDepthCamera_r 203 30.1406`
- `camera/color/pikaGripperFisheyeCamera_l 0 -nan`
- `camera/color/pikaGripperFisheyeCamera_r 0 -nan`

`capture_timing.log`：

- `16:57:28` `capture_object_created`
- `16:57:35` `capture_shutdown_begin`
- `16:57:35` `capture_shutdown_done`

实际磁盘文件计数：

- `camera/color/myD435`: 159
- `camera/color/pikaGripperDepthCamera_l`: 178
- `camera/color/pikaGripperDepthCamera_r`: 174
- `camera/depth/pikaGripperDepthCamera_l`: 175
- `camera/depth/pikaGripperDepthCamera_r`: 174

## hz 状态日志结论

来源：`$HOME/agilex/data/capture_status_hz.log`

在 `16:57:29` 到 `16:57:35` 这次 episode26 的状态中：

- `fail=false`
- 直到退出前都不是“频率阈值失败停采”
- `16:57:35.836448` 出现 `quit=true`
- 随后 `16:57:35.836605` 变成空 topics 状态
- `16:57:38` 之后采集器重启并重新发布状态

同时可以看到：

- `/gripper/camera_fisheye_l/color/image_raw` 一直是 `NaN`
- `/gripper/camera_fisheye_r/color/image_raw` 一直是 `NaN`
- `/joint_states_gripper_l`、`/joint_states_gripper_r` 在这次日志里是 `NaN`
- `/piper_IK_l/receive_end_pose_orient`、`/piper_IK_r/receive_end_pose_orient` 在这次日志里是 `NaN`

但这些并没有触发 `fail=true`，说明不是这次提前结束的直接原因。

## 结论

`episode26` 录制过短的直接原因不是 `s6` 结束得太早，也不是新的“取消 hz 阈值”逻辑失效，而是：

1. `s6` 在 `16:57:28` 正常发起开始
2. `s5` 在 `16:57:28` 正常创建 `episode26`
3. `data_tools_dataCapture` 在大约 `16:57:35` 异常退出，tmux 中表现为 `exit code -11`
4. 采集进程重启后，原来的 `episode26` 已经结束
5. 用户在 `16:58:14` 再踩停止时，旧服务连接已经失效，所以 `s6` 报 stop failed

因此，`episode26` 只录到约 6 秒，是因为采集进程本身崩溃提前结束，不是脚踏板开始/结束时间错误，也不是渲染脚本少拼了一部分。

## 当前判断

- 这次问题的根因更接近 `data_tools_dataCapture` 自身崩溃
- 不是频率阈值逻辑
- 不是 `s6` 提前 stop
- 不是“录了很长但只导出了中间一段”
