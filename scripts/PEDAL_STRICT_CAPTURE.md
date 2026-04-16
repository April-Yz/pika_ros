# 脚踏板严格控制采集

这套入口不改原来的 `s5`、`s6` 文件，只额外增加一套新的 `s5` 启动方式。

目标：

- 不因为 topic 频率过低自动停止采集
- 严格以 `s6` 脚踏板开始/结束结果为准
- 额外记录采集期间 `/data_tools_dataCapture/status` 里的 hz 变化

## 使用方式

前面的 `s1` 到 `s4` 保持原来的启动方式不变。

### 终端 5：新的严格版采集

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_s5_pedal_strict_capture.bash $HOME/agilex/data
```

默认会启动：

- D435 ROS 节点
- `data_tools_dataCapture`
- `capture_status_hz_logger.py`

### 终端 6：脚踏板控制

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
sudo -E bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data
```

右踏板 `KEY_C`：

- 踩一下：开始采集
- 再踩一下：结束采集

## 日志文件

数据集根目录下会有：

- `foot_pedal_capture.log`
  记录脚踏板按下、开始请求、结束请求、服务成功/失败
- `capture_service.log`
  记录采集服务收到的 start/end 请求
- `capture_service_requests.log`
  记录每次 service 调用的 `callerid`、`start`、`end`、`episode_index`、`dataset_dir`、`instructions`
- `capture_status_hz.log`
  记录 `/data_tools_dataCapture/status` 中每次发布的 `topics`、`count_in_seconds`、`frequencies`、`fail`、`quit`

每个 `episodeN` 目录下还会有：

- `capture_timing.log`
- `statistic.txt`

## 关键文件

- `scripts/start_s5_pedal_strict_capture.bash`
- `scripts/capture_status_hz_logger.py`
- `src/data_tools/launch/run_data_capture_multi_pika_teleop_d435_no_hz_limit.launch`
- `src/data_tools/launch/run_data_capture_multi_pika_teleop_with_d435_pedal_strict.launch`

## 说明

这套入口只是不再让 `data_tools_dataCapture` 因 `hz` 阈值失败而自动停采。

如果上游 topic 本身没发布、设备掉线、或者 ROS 节点崩溃，采集结果仍然会受影响。`capture_status_hz.log` 的目的就是把这些变化完整记下来，方便之后对齐脚踏板时间和实际数据缺失时间。
