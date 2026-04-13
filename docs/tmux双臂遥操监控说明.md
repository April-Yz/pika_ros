# tmux 双臂遥操监控说明

本文档说明双臂监控脚本：

- `scripts/monitor_dual_piper_lowfreq_tmux.bash`
- `scripts/monitor_dual_piper_tmux.bash`
- `scripts/open_dual_piper_low_view.bash`

适用场景：

- 双 `sense` 控双 `Piper`
- 需要快速判断左臂还是右臂链路有问题
- 需要低频观察，不想看高频 `rostopic echo`

## 一、怎么启动

### 1. 低频监控

如果你当前 shell 是 `zsh`：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash
tmux attach -t piper-dual-low
```

如果你想直接打开一个单独 view，不想自己手动 `tmux new-session`：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/open_dual_piper_low_view.bash
```

这个命令会：

- 没有 `piper-dual-low` 时先创建低频监控
- 自动创建一个新的 linked session，默认名是 `piper-dual-low-4`
- 直接 attach 到这个新 view

### 2. 详细监控

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_tmux.bash
tmux attach -t piper-dual-mon
```

## 二、低频窗口说明

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

每秒打印一次左右两边两类夹爪数据：

- `sensor->arm gripper`
  - 来自 `/joint_states_gripper_l`、`/joint_states_gripper_r`
  - 表示手持 `sensor` 侧送给双臂控制链路的夹爪命令
- `gripper device`
  - 来自 `/joint_states_single_gripper_l`、`/joint_states_single_gripper_r`
  - 表示 `start_multi_gripper.bash` 这一路设备链路的输出

看法：

- `sensor->arm` 无数据
  - 说明 `start_multi_sensor.bash sensor` 这一路没正常发
- `gripper device` 无数据
  - 说明 `start_multi_gripper.bash gripper sensor` 这一路没正常发

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

### 6. `hz`

这个窗口看左右关键 topic 的频率：

- `/pika_pose_l`
- `/pika_pose_r`
- `/piper_IK_l/ctrl_end_pose`
- `/piper_IK_r/ctrl_end_pose`
- `/joint_states_gripper_l`
- `/joint_states_gripper_r`
- `/joint_states_single_gripper_l`
- `/joint_states_single_gripper_r`

适合快速判断是 `sensor` 路掉频，还是 `gripper` 路掉频。

## 三、详细监控窗口说明

`monitor_dual_piper_tmux.bash` 会创建这些窗口：

- `pose`
  - 低频看左右 `FK / CTRL / DIFF`
- `gripper`
  - 低频看 `sensor->arm gripper` 和 `gripper device`
- `status`
  - 低频看 `teleop` 和 `over_limit`
- `localization`
  - 直接看 `/pika_localization_status_l`、`/pika_localization_status_r`
- `target`
  - 直接看 `/piper_IK_l/ctrl_end_pose`、`/piper_IK_r/ctrl_end_pose`
- `feedback`
  - 直接看 `/joint_states_single_l`、`/joint_states_single_r`
- `output`
  - 直接看 `/joint_states_l`、`/joint_states_r`
- `hz`
  - 看左右输入、目标、命令、反馈频率
- `trigger_l`
  - 手动执行 `rosservice call /teleop_trigger_l "{}"`
- `trigger_r`
  - 手动执行 `rosservice call /teleop_trigger_r "{}"`

## 四、旧单臂监控在双臂中是否还有作用

- `piper-jitter`
  - 主要针对单臂，不适合直接看双臂
- `piper-low`
  - 单臂低频监控，不适合双臂
- `piper-mon`
  - 单臂原始 topic 监控，只适合单臂 spot check

双臂请优先使用：

- `piper-dual-low`
- `piper-dual-mon`

## 五、现在这套系统怎么理解

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

## 六、当前你这次问题的结论

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
