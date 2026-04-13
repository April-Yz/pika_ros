# tmux 单臂遥操监控说明

本文档说明如何查看两个 tmux 监控脚本：

- `scripts/monitor_single_piper_tmux.bash`
- `scripts/monitor_single_piper_lowfreq_tmux.bash`

前者适合排查完整链路，后者适合低频盯关键结果。

## 一、怎么启动

如果你当前 shell 是 `zsh`，建议这样启动：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
tmux attach -t piper-mon
```

低频版启动：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_lowfreq_tmux.bash
tmux attach -t piper-low
```

如果你当前 shell 是 `bash`，可以改成：

```bash
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.bash bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
tmux attach -t piper-mon
```

## 二、tmux 基本操作

- 切到下一个窗口：`Ctrl-b` 然后按 `n`
- 切到上一个窗口：`Ctrl-b` 然后按 `p`
- 直接跳到指定窗口：`Ctrl-b` 然后按数字
- 暂时离开 tmux：`Ctrl-b` 然后按 `d`
- 重新进入：`tmux attach -t piper-mon`
- 关闭监控：`tmux kill-session -t piper-mon`

低频版对应：

- 重新进入：`tmux attach -t piper-low`
- 关闭监控：`tmux kill-session -t piper-low`

## 三、每个窗口怎么看

这一节先说完整监控 `piper-mon`。

### 1. `summary`

这是总览窗口。

它主要看两件事：

- 关键节点在不在
- 关键 topic 在不在

如果这里已经看不到 `/pika_pose`、`/teleop_status`、`/arm_control_status`、`/piper_IK/ctrl_end_pose`，说明链路本身就没起来。

### 2. `loc_status`

看 `/pika_localization_status`。

重点字段：

- `accurate: True`
  - 说明定位节点认为当前定位可信
- `accurate: False`
  - 说明当前定位不可信，遥操位置控制通常会受影响

注意：

- 即使这里是 `True`，如果 `s2` 里还在频繁打印 “The data fluctuates too much...”，也说明定位有明显抖动风险

### 3. `teleop_status`

看 `/teleop_status`。

重点字段：

- `fail: False`
- `quit: False`

一般表示 teleop 当前处于工作态。

如果没有任何输出，通常表示：

- 还没触发 teleop
- 或 teleop 节点没有进入发布状态

### 4. `arm_status`

看 `/arm_control_status`。

重点字段：

- `over_limit: False`
  - IK 接受了当前目标
- `over_limit: True`
  - IK 拒绝了当前目标，机械臂不会跟过去

你现在最关键的问题就在这里。
目前已经确认你的系统会持续出现 `over_limit: True`。

### 5. `pika_pose`

看 `/pika_pose`。

这是遥操输入端的末端位姿来源。

你主要看：

- 有没有持续输出
- 位姿是否抖得很厉害

如果这里跳动很大，机械臂目标也会跟着跳。

### 6. `ctrl_pose`

看 `/piper_IK/ctrl_end_pose`。

这是 teleop 节点真正发给 IK 的目标末端位姿，也就是 IK 希望机械臂末端到达的位置。

你主要看：

- 有没有输出
- 输出是否连续
- 坐标有没有突然大跳

如果这里没输出，说明 teleop 没真正工作。
如果这里有输出，但 `arm_status` 还是一直 `over_limit: True`，说明问题已经进入 IK 求解阶段。

补充：

- 这里看的是 `EE pose`
- 不是关节角
- 表达形式是 `geometry_msgs/PoseStamped`
- 其中位置是 `x y z`
- 姿态是四元数，完整监控直接显示原始消息

### 7. `fk_pose`

看 `/piper_FK/urdf_end_pose_orient`。

这是当前机械臂真实关节经过 FK 算出来的末端位姿。

你可以把它和 `ctrl_pose` 对比：

- 如果两者差很小，但还是 `over_limit: True`
  - 说明不像是“目标太远”，更像 IK 初值或碰撞判定有问题

### 8. `joint_in`

看 `/joint_states_single`。

这是机械臂当前真实关节角。

它反映的是：

- 机械臂自己当前在哪
- 这是当前真实关节角，不是 IK 目标

### 9. `joint_out`

看 `/joint_states_gripper`。

这是最终送给 `piper_ctrl_single_node` 的控制输入。

它是：

- 前 6 个关节来自机械臂侧
- 第 7 个夹爪开口来自 sense/gripper 侧合并后的值

如果这个窗口长期没输出，机械臂控制节点就收不到实际控制量。

补充：

- 对单臂 Piper 来说，IK 成功后最终会形成关节角命令
- 关节角表达看的是这类 `JointState`
- 但“遥操设备想让机械臂去哪里”首先看 `ctrl_pose`，不是先看这里

### 10. `hz`

看几个关键 topic 的频率。

你主要看：

- `/pika_pose`
- `/piper_IK/ctrl_end_pose`
- `/joint_states_single`
- `/joint_states_gripper`

如果某个 topic 频率突然掉到很低甚至没有，说明该链路断了。

### 11. `trigger`

这是手动触发窗口。

你可以直接在里面执行：

```bash
rosservice call /teleop_trigger "{}"
```

这个用于排查“双击没有成功触发 teleop”。

## 四、你当前系统应该怎么看

按现在的排查结果，你最该盯的是这 4 个窗口：

1. `teleop_status`
2. `ctrl_pose`
3. `arm_status`
4. `fk_pose`

判断逻辑：

1. `teleop_status` 没输出
   - 先怀疑 teleop 没触发
2. `teleop_status` 有输出，但 `ctrl_pose` 没输出
   - 说明 teleop 没产出目标位姿
3. `ctrl_pose` 有输出，但 `arm_status` 一直 `over_limit: True`
   - 说明 IK 拒绝目标
4. `ctrl_pose` 和 `fk_pose` 很接近，但还是 `over_limit: True`
   - 高概率是 IK 初值、碰撞判定、姿态映射的问题

## 四、低频版 `piper-low` 怎么看

低频版主要是为了人眼能跟上，不会像 `rostopic echo` 一样刷太快。

它有 4 个窗口：

### 1. `pose`

这是最关键的低频窗口，每秒打印一次。

它显示三行：

- `FK`
  - 机械臂当前实际末端位姿
  - 来源：`/piper_FK/urdf_end_pose_orient`
- `CTRL`
  - teleop 发给 IK 的目标末端位姿
  - 来源：`/piper_IK/ctrl_end_pose`
- `DIFF`
  - 目标减实际的差值

这里的 `CTRL` 就是你问的“遥操设备传过去、IK 想让它到的位置”。

注意：

- 这里看的是末端位姿 `EE pose`
- 不是关节角
- 位置单位是米
- 姿态显示为 `roll pitch yaw`

### 2. `gripper`

每秒打印一次夹爪开口。

- `sense 夹爪开口`
  - 遥操端当前夹爪开口
  - 来源：`/sensor/gripper/joint_state`
- `合并后 joint6/7 开口`
  - 合并后的控制开口
  - 来源：`/joint_states_single_gripper`

### 3. `status`

每秒打印一次关键状态：

- `localization accurate`
- `teleop (fail, quit)`
- `arm over_limit`

如果这里一直是 `arm over_limit: True`，就说明 IK 一直在拒绝目标。

### 4. `trigger`

这个窗口不自动刷数据，只是给你手动触发 teleop：

```bash
rosservice call /teleop_trigger "{}"
```

## 五、你要看“IK 失败的位置”时看哪里

先分清 3 种东西：

### 1. 遥操设备当前位姿

看 `/pika_pose`。

这是定位系统给出的遥操端位姿原始输入。

### 2. teleop 变换后的机械臂目标位姿

看 `/piper_IK/ctrl_end_pose`。

这是最关键的“目标位置”。

也就是：

- 遥操设备经过相对位姿映射后
- 真正送给 IK 的末端目标

如果你想知道“IK 失败时它到底想去哪里”，优先看这个 topic。

### 3. IK 求解成功后形成的关节角命令

看 `/joint_states_gripper` 或相关 `JointState` 输出。

这是关节角表达，不是末端位姿表达。

所以结论是：

- 想看“它想去哪里”：看 `ctrl_pose` 或 `piper-low` 的 `pose` 窗口里的 `CTRL`
- 想看“机械臂现在在哪”：看 `fk_pose` 或 `piper-low` 的 `pose` 窗口里的 `FK`
- 想看“IK 有没有真的解出关节角”：看 `joint_out` 和 `arm_status`

## 六、s2 和 s3 正常分别负责什么

### 1. `s2`

通常是传感器链路。

你这里主要负责：

- 启动 sense 侧数据采集
- 启动 gripper 侧数据采集
- 启动定位和相机相关节点
- 产出 `/pika_pose`、`/pika_localization_status`、夹爪开口等上游输入

如果 `s2` 出问题，常见现象是：

- `/pika_pose` 没有输出
- 定位漂移很大
- `accurate` 不稳定
- 相机节点重启
- fish-eye/usb camera 缺模块

### 2. `s3`

通常是机械臂 teleop 和控制链路。

你这里主要负责：

- 启动 `teleop_piper_publish.py`
- 启动 `piper_IK.py`
- 启动 `piper_FK.py`
- 启动 `piper_ctrl_single_node.py`

也就是把：

- `s2` 给出的遥操输入

变成：

- IK 目标末端位姿
- FK 当前末端位姿
- 最终机械臂关节控制命令

如果 `s3` 出问题，常见现象是：

- `/piper_IK/ctrl_end_pose` 没输出
- `/arm_control_status` 一直 `over_limit: True`
- 机械臂已使能但不动
- 夹爪可能还能同步，但手臂位置不跟

## 七、你现在已经确认到的现象

当前已经确认：

- `/pika_pose` 正在发布
- `/pika_localization_status` 会报 `accurate: True`
- `rosservice call /teleop_trigger "{}"` 后，`/teleop_status` 会开始输出
- `/piper_IK/ctrl_end_pose` 会持续输出
- 但 `/arm_control_status` 持续为 `over_limit: True`

所以目前不是“没有控制信号”，而是“控制信号到了 IK，但被 IK 拒绝了”。
