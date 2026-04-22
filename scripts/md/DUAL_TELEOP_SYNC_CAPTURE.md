# 双臂同步采集说明

## 一、为什么之前会报错

你之前在 `zsh` 里执行了：

```bash
source ~/pika_ros/install/setup.bash
```

这是给 `bash` 用的。在 `zsh` 里应改为：

```bash
source ~/pika_ros/install/setup.zsh
```

否则工作区环境不会正确加载，后面的：

```bash
roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch ...
```

就会报“找不到 launch 文件”。

## 二、前置检查

先确认 D435 已被系统识别：

```bash
rs-enumerate-devices -s
```

应能看到序列号：

```text
817412070803
```

还要确认：

- 左右 sensor 已正确绑定
- 左右 gripper 已正确绑定
- 双臂 teleop 本身可以正常启动

## 三、终端 1 到 6 的启动顺序

### 终端 1：启动 ROS Master

```bash
roscore
```

### 终端 2：启动双 sensor

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_multi_sensor_sync_capture.bash sensor
```

### 终端 3：启动双 gripper

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_multi_gripper_sync_capture.bash gripper
```

### 终端 4：启动双臂遥操

```bash
conda activate pika
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
roslaunch pika_remote_piper teleop_rand_multi_piper.launch
```

### 终端 5：启动带 D435 的数据采集服务

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
  serial_no:=817412070803 \
  datasetDir:=$HOME/agilex/data \
  episodeIndex:=0 \
  useService:=true
```

### 终端 6：启动双臂同步录制控制

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_dual_teleop_capture_sync.bash $HOME/agilex/data
```

## 四、实际录制逻辑

这套同步采集逻辑下：

- 只启动左手遥操：不会开始录制
- 只启动右手遥操：不会开始录制
- 左右手都进入遥操状态：自动开始录制
- 任意一只手退出遥操：自动停止录制

同步节点监控的是：

```text
/teleop_status_l
/teleop_status_r
```

## 五、建议观察的 topic

查看左右手 teleop 状态：

```bash
rostopic echo /teleop_status_l
rostopic echo /teleop_status_r
```

查看 D435 话题是否正常：

```bash
rostopic hz /camera/color/image_raw
rostopic echo -n 1 /camera/color/camera_info
```

查看当前生成的数据集目录：

```bash
ls -d $HOME/agilex/data/episode*
```

## 六、保存位置

录制结果保存在：

```text
$HOME/agilex/data/episodeN
```

同步录制脚本会自动扫描当前目录下已有的 `episode` 编号，并从最大编号的下一个开始继续保存。
