# tmux 双臂遥操监控说明

本文档说明双臂低频监控脚本：

- `scripts/monitor_dual_piper_lowfreq_tmux.bash`

适用场景：

- 双 `sense` 控双 `Piper`
- 需要快速判断左臂还是右臂链路有问题
- 需要低频观察，不想看高频 `rostopic echo`

## 一、怎么启动

如果你当前 shell 是 `zsh`：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash
tmux attach -t piper-dual-low
```

## 二、窗口说明

### 1. `pose`

每秒打印一次左右两臂的：

- `FK`
  - 当前真实末端位姿
- `CTRL`
  - 发给 IK 的目标末端位姿
- `DIFF`
  - 目标与实际的差值

看法：

- 左臂不动就盯 `LEFT`
- 右臂不动就盯 `RIGHT`
- `CTRL` 无数据通常表示对应 teleop 没触发或上游没输入

### 2. `gripper`

每秒打印一次左右两边最终控制夹爪开口：

- `LEFT gripper`
- `RIGHT gripper`

如果一侧长期无数据，通常说明对应 `serial_gripper_imu_*` 没正常发布。

### 3. `status`

每秒打印一次左右两边：

- `teleop (fail, quit)`
- `arm over_limit`

判断逻辑：

- `teleop` 没数据或一直 `fail`
  - 对应侧 teleop 没进入工作态
- `over_limit=True`
  - 对应侧 IK 拒绝目标

### 4. `trigger_l`

手动触发左臂 teleop：

```bash
rosservice call /teleop_trigger_l "{}"
```

### 5. `trigger_r`

手动触发右臂 teleop：

```bash
rosservice call /teleop_trigger_r "{}"
```

## 三、现在这套系统怎么理解

双臂版最关键的是左右链路是分开的：

- 左臂：
  - `/pika_pose_l`
  - `/joint_states_gripper_l`
  - `/piper_IK_l/ctrl_end_pose`
  - `/piper_FK_l/urdf_end_pose_orient`
- 右臂：
  - `/pika_pose_r`
  - `/joint_states_gripper_r`
  - `/piper_IK_r/ctrl_end_pose`
  - `/piper_FK_r/urdf_end_pose_orient`

所以你排查时要先看：

1. 左右哪一侧先断
2. 是 `CTRL` 无数据，还是 `FK` 不跟
3. 是夹爪输入没来，还是 IK/执行侧没跟

## 四、当前你这次问题的结论

重新绑定后，串口映射已经恢复：

- `/joint_states_gripper_l` 有发布者
- `/joint_states_gripper_r` 有发布者
- `/dev/ttyUSB50`
- `/dev/ttyUSB51`

但鱼眼相机映射仍然不对：

- `s2` 还在找 `/dev/video51`
- 当前系统里没有 `/dev/video50`、`/dev/video51`
- 实际创建出来的是别的 video 设备编号或其他软链接

所以现在更像是：

- 夹爪串口链路恢复了
- 右侧鱼眼/定位链路还没恢复
