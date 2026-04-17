# 脚踏板记录

## 设备识别结果

当前脚踏板被系统识别为一组复合输入设备：

```text
/dev/input/event6   PCsensor FootSwitch Keyboard
/dev/input/event7   PCsensor FootSwitch Mouse
/dev/input/event21  PCsensor FootSwitch
```

建议后续脚本使用稳定路径，而不是直接写死 `event6`：

```text
/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd
```

系统中的稳定软链接：

```text
/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd   -> ../event6
/dev/input/by-id/usb-PCsensor_FootSwitch-event-mouse -> ../event7
/dev/input/by-id/usb-PCsensor_FootSwitch-event-if01  -> ../event21
```

## 三个踏板映射

通过 `sudo evtest /dev/input/event6` 实测，按左中右顺序踩踏板，对应键值如下：

- 左踏板：`KEY_A`
- 中踏板：`KEY_B`
- 右踏板：`KEY_C`

对应的事件码：

- 左踏板：`code 30 (KEY_A)`
- 中踏板：`code 48 (KEY_B)`
- 右踏板：`code 46 (KEY_C)`

## 当前控制策略

当前使用左、右踏板：

- 左踏板 `KEY_A`：读取当前机器人状态快照，并写入数据目录下的状态 `log/md`
- 右踏板 `KEY_C`：第一次踩下开始采集
- 右踏板 `KEY_C`：第二次踩下结束采集

当前中踏板先空着，不做任何动作：

- 中踏板 `KEY_B`：忽略

## 手动测试命令

查看设备：

```bash
ls -l /dev/input/by-id/ | grep -i FootSwitch
```

测试按键映射：

```bash
sudo evtest /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd
```

## 右踏板采集控制脚本

脚本路径：

```text
~/pika_ros/scripts/foot_pedal_capture_toggle.py
```

启动方式：

```bash
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
/usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py
```

如果要指定数据集目录：

```bash
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
/usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py \
  --dataset-dir ~/agilex/data
```

脚本启动后行为：

- 监听 `/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd`
- 响应左踏板 `KEY_A` 和右踏板 `KEY_C`
- 左踏板会抓取当前 `joint_states_single*`、`piper_FK*/urdf_end_pose_orient`、`sensor/gripper*` 等可用状态
- 左踏板快照输出到 `datasetDir/foot_pedal_state_snapshot.log` 和 `datasetDir/foot_pedal_state_snapshot.md`
- 自动调用 `/data_tools_dataCapture/capture_service`
- 自动从当前最大 `episode` 后面继续编号

如果直接访问输入设备时报权限错误，可以直接用：

```bash
sudo /usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py \
  --dataset-dir ~/agilex/data
```

当前脚本已经内置 ROS Python 路径补全，所以即使直接用上面这条 `sudo` 命令，也能正常导入 `rospy`。

## 日志观察

脚本日志会打印：

- 脚踏板设备路径
- 当前右踏板触发
- 开始采集对应的 `episode`
- 停止采集
- 服务调用失败或采集服务不可用
