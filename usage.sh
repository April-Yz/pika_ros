(base) piper@Compineter:~$ conda deactivate  #退出虚拟环境
piper@Compineter:~$ cd ~/pika_ros/scripts/
piper@Compineter:~/pika_ros/scripts$ python3 setup_device.py
=== pika配置工具 ===
请选择绑定
1.两个pika sensor(手持夹爪)
2.两个pika gripper(安装于机械臂上的夹爪)
3.一个pika sensor 一个pika gripper
请输入：1
请插入左设备，然后按回车键继续...

正在获取左设备信息...
寻找鱼眼摄像头，请在出现鱼眼摄像头时按下s，非鱼眼摄像头则按下q(注意在图像窗口按 下，不要在终端！！！)
左设备信息: 315122271385 1-2.4:1.0 1-2.1:1.0
请拔出左设备，插入右设备（注意不要插在同一个USB口，配置完成后USB口不能改变），然后按回车键继续...

正在获取右设备信息...
寻找鱼眼摄像头，请在出现鱼眼摄像头时按下s，非鱼眼摄像头则按下q(注意在图像窗口按 下，不要在终端！！！)
右设备信息: 412622273408 1-1.4:1.0 1-1.1:1.0
正在生成配置文件...
配置完成！已生成以下文件：
1. setup_multi_sensor.bash
2. start_multi_sensor.bash
执行setup_multi_sensor.bash
[sudo] piper 的密码：
执行完成。
请拔插设备，注意插入先前绑定的同一个USB口。然后按回车键检查是否绑定成功...

请等待...
找不到sensor（左）鱼眼
请拔插设备，注意插入先前绑定的同一个USB口。然后按回车键检查是否绑定成功...

请等待...
绑定成功，启动设备方法：
2. 然后运行: bash start_multi_sensor.bash
piper@Compineter:~/pika_ros/scripts$ tmux set -g mouse on
piper@Compineter:~/pika_ros/scripts$


#基站校准
cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate


python3 /home/piper/pika_ros/scripts/setup_device.py --calibrate_base

cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate

# 设置左右手
echo 'export pika_L_code=LHR-2D0CBC1B' >> ~/.bashrc
echo 'export pika_R_code=LHR-6969B743' >> ~/.bashrc
source ~/.bashrc

roslaunch pika_locator pika_double_locator.launch

# 一只手一直sensor启动
cd ~/pika_ros/scripts/ && bash start_sensor_gripper.bash


# 启动臂通信
cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros

bash can_activate.sh can0 1000000

rostopic pub /joint_states sensor_msgs/Jointstate "header:
seq: 0
stamp:{secs:0,nsecs:0}
frame id:''
name:['']
position:[1.2]
velocity:[0]
effort:[0]"




# 配置一个夹爪一个传感器
# 可以遥操单纯夹爪
cd ~/pika_ros/scripts/ && bash start_sensor_gripper.bash


roscore


conda deactivate
source ~/pika_ros/install/setup.bash
cd ~/pika_ros/scripts && bash start_sensor_gripper.bash

source ~/pika_ros/install/setup.bash
conda activate pika
roslaunch pika_remote_piper teleop_rand_single_piper.launch

# 可视化数据
  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
  tmux attach -t piper-mon

PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
tmux attach -t piper-mon


# 基站 
cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate
# can
cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros

bash can_activate.sh can0 1000000


roscore

# 终端2
  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  cd ~/pika_ros/scripts
  bash start_sensor_gripper.bash

# 终端3
   conda activate pika
  source ~/pika_ros/install/setup.zsh
  roslaunch pika_remote_piper teleop_rand_single_piper.launch


# 监控
  tmux kill-session -t piper-mon
  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
  tmux attach -t piper-mon
  # 低频监控
  tmux kill-session -t piper-low
  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_lowfreq_tmux.bash
  tmux attach -t piper-low

#排查抖动原因
  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_jitter_tmux.bash
  tmux attach -t piper-jitter

# 录制60s
  RECORD_SECONDS=60 PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/record_single_piper_debug.bash

  tmux kill-session -t piper-low

rosservice call /teleop_trigger "{}"

    source ~/pika_ros/install/setup.zsh
    rosservice call /teleop_trigger "{}"


#     先取当前真实关节角：

  source ~/pika_ros/install/setup.zsh
  rostopic echo -n 1 /joint_states_single
  
#   header: 
#   seq: 460069
#   stamp: 
#     secs: 1775827391
#     nsecs: 621035575
#   frame_id: ''
# name: 
#   - joint0
#   - joint1
#   - joint2
#   - joint3
#   - joint4
#   - joint5
#   - joint6
# position: [-0.087028116, -0.036527736, 0.0055820800000000005, -0.09969246000000001, 0.552224708, 0.13283606, 0.0]
# velocity: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
# effort: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

  source ~/pika_ros/install/setup.zsh
  rostopic pub -r 20 /joint_states_gripper sensor_msgs/JointState "header:
    stamp: now
    frame_id: ''
  name: []
  position: [-0.037028116, -0.036527736, 0.0055820800000000005, -0.09969246000000001, 0.552224708, 0.13283606, 0.0]
  velocity: []
  effort: []"