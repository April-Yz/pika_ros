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




# 设置端口
  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
cd ~/pika_ros/scripts/
python3 setup_device.py



# 基站 
cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate
# can
cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros
bash can_activate.sh can0 1000000

#  双臂can
cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros
bash find_all_can_port.sh
cd ~/pika_ros/src/PikayiAnyArm/piper/piper_ros
bash can_config.sh

# roscore
# # 终端2
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
#   cd ~/pika_ros/scripts
#   bash start_sensor_gripper.bash


# # 终端3
#    conda activate pika
#   source ~/pika_ros/install/setup.zsh
#   roslaunch pika_remote_piper teleop_rand_single_piper.launch

# # 双臂 s2
# # conda deactivate
# # source ~/pika_ros/install/setup.bash
# # cd ~/pika_ros/scripts && bash start_multi_sensor.bash
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
#   cd ~/pika_ros/scripts
#   bash start_multi_sensor.bash

# # s3
# # source ~/pika_ros/install/setup.bash
# # conda activate pika
# # roslaunch pika_remote_piper teleop_rand_multi_piper.launch

#   conda activate pika
#   source ~/pika_ros/install/setup.zsh
#   roslaunch pika_remote_piper teleop_rand_multi_piper.launch

# # 监控
#   tmux kill-session -t piper-mon
#   PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_tmux.bash
#   tmux attach -t piper-mon
#   # 低频监控
#   tmux kill-session -t piper-low
#   PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_single_piper_lowfreq_tmux.bash
#   tmux attach -t piper-low

# # 
# 终端1：
# Plain Text
# 复制代码
# 1
# roscore
# 终端2：
# Plain Text
# 复制代码
# 1
# 2
# 3
# conda deactivate
# source ~/pika_ros/install/setup.bash
# cd ~/pika_ros/scripts && bash start_multi_sensor.bash sensor
# 终端3：
# Plain Text
# 复制代码
# 1
# 2
# 3
# conda deactivate
# source ~/pika_ros/install/setup.bash
# cd ~/pika_ros/scripts && bash start_multi_gripper.bash gripper sensor
# 终端4：
# Plain Text
# 复制代码
# 1
# 2
# 3
# source ~/pika_ros/install/setup.bash
# conda activate pika
# roslaunch pika_remote_piper teleop_rand_multi_piper.launch

#



  1. 先杀掉旧 session

  tmux kill-session -t piper-dual-low

  2. 重新创建

  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash

  3. 如果你想两个终端分别看不同窗口，不要同时 attach 同一个 session，改成再建一个“链接 session”：

  tmux new-session -d -t piper-dual-low -s piper-dual-low-2
  tmux attach -t piper-dual-low

  另一个终端：

  tmux attach -t piper-dual-low-2

tmux new-session -d -t piper-dual-low -s piper-dual-low-4
  tmux attach -t piper-dual-low-4



# 双臂监控
PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash
tmux attach -t piper-dual-low

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


    1. 先把文件加入暂存区

  cd ~/pika_ros
  git add .

  2. 做第一次提交

  git config user.name "April-Yz"
  git config user.email "2979193155@qq.com"

  git commit -m "Initial import of local pika_ros workspace"

  ssh-keygen -t ed25519 -C "2979193155@qq.com piper"





# all in one
  bash /home/piper/pika_ros/scripts/start_dual_piper_tmux.bash
  tmux attach -t piper-dual-run


 启动命令：

  bash /home/piper/pika_ros/scripts/start_dual_piper_tmux.bash

  默认会创建：

  - dual-s1
  - dual-s2
  - dual-s3
  - dual-s4

  分别进入：

  tmux attach -t dual-s1
  tmux attach -t dual-s2
  tmux attach -t dual-s3
  tmux attach -t dual-s4

  s1 里已经包含：

  - # Step 1 启动机械臂 CAN 通信
  - # Step 2 启动 roscore

  也就是先跑：

  cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros
  bash can_config.sh

  再启动 roscore。

  清理脚本也补上了：

  pika_ros/scripts/cleanup_dual_piper_tmux.bash

  用法：

  bash /home/piper/pika_ros/scripts/cleanup_dual_piper_tmux.bash

  它会清理这些双臂运行/监控 session：

  - dual-s1
  - dual-s2
  - dual-s3
  - dual-s4
  - piper-dual-low
  - piper-dual-low-2
  - piper-dual-low-3
  - piper-dual-low-4
  - piper-dual-low-5
  - piper-dual-mon

  双臂监控这边现在建议这样用：

  低频监控：

  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash
  tmux attach -t piper-dual-low

  直接开一个新的 low 视图，不用你手工 new-session：

  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/open_dual_piper_low_view.bash

  详细监控：

  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_tmux.bash
  tmux attach -t piper-dual-mon

  你前面问的那个关键点，现在答案是：
  之前版本的 s1/s2/s3/s4 不是独立的；现在已经改成独立的了。

  如果你要，我下一步可以再给你补一个总控脚本，比如：

  - 先 cleanup
  - 再 start_dual_piper_tmux
  - 再自动创建 piper-dual-low
  - 再自动创建 piper-dual-mon

  变成真正的一条命令全启动。





    source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  rostopic echo /pika_localization_status_l
  rostopic echo /pika_localization_status_r




   我这边也做了 roslaunch --nodes 校验，launch 可以正常解析。

  如果你的 D435 话题名就是默认这组：

  - /d435/color/image_raw
  - /d435/color/camera_info

  那双臂遥操作采集直接这样起：

  source ~/pika_ros/install/setup.bash
  roslaunch data_tools run_data_capture_multi_pika_teleop_d435.launch \
    useService:=true \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=0

  如果你的 D435 话题不是这个名字，先查一下：

  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  rostopic list | grep -E 'color/image_raw|color/camera_info'

  然后把真实话题传进去，比如：

  source ~/pika_ros/install/setup.bash
  roslaunch data_tools run_data_capture_multi_pika_teleop_d435.launch \
    useService:=true \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=0 \
    d435_name:=myD435 \
    d435_frame:=camera_color_optical_frame \
    d435_color_topic:=/camera/color/image_raw \
    d435_color_info_topic:=/camera/color/camera_info

  单臂版本同理：

  source ~/pika_ros/install/setup.bash
  roslaunch data_tools run_data_capture_single_pika_teleop_d435.launch \
    useService:=true \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=0 \
    d435_name:=myD435 \
    d435_frame:=camera_color_optical_frame \
    d435_color_topic:=/camera/color/image_raw \
    d435_color_info_topic:=/camera/color/camera_info

  补充两点：

  - 我这边当前运行时没有扫到现成的 D435 ROS 话题，所以你启动前最好先用 rostopic
    list 确认真实话题名。
  - 这版只额外保存了 D435 的彩色画面。如果你还想把 D435 的深度图一起存进去，我可以
    在不动原文件的前提下再给你加一套 depth 版 launch。



# D435
  pika_ros/install/share/data_tools/launch/run_data_capture_multi_pika_teleop_with_d435.launch

# 校准基站

cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate

# 校准手
python3 /home/piper/pika_ros/scripts/setup_device.py --calibrate_base

# 检查相机
  ls -l /dev/ttyUSB50 /dev/ttyUSB51 /dev/ttyUSB60 /dev/ttyUSB61 /dev/video50 /dev/video51 /dev/video60 /dev/video61
  udevadm info /dev/ttyUSB50 | grep DEVPATH
  udevadm info /dev/ttyUSB51 | grep DEVPATH
  udevadm info /dev/ttyUSB60 | grep DEVPATH
  udevadm info /dev/ttyUSB61 | grep DEVPATH
  udevadm info /dev/video50  | grep DEVPATH
  udevadm info /dev/video51  | grep DEVPATH
  udevadm info /dev/video60  | grep DEVPATH
  udevadm info /dev/video61  | grep DEVPATH
cd ~/pika_ros/src/PikaAnyArm/piper/piper_ros
bash can_config.sh








lsusb
  启动方式：

  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  /usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py

  或者用包装脚本：

  bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash

  如果你要指定数据集目录：

  bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data

在你正常启动完 s1 s2 s3 s4 之后，现在只需要再开两个终端。

  终端 5：启动录制服务和 D435

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

  终端 6：启动脚踏板采集控制

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data

  然后你就用右踏板 KEY_C 控制：

  - 踩一下：开始采集
  - 再踩一下：结束采集

  左踏板和中踏板现在不做任何事。

  如果你想看脚踏板控制日志，就看终端 6。正常会打印类似：

  - Listening to foot pedal device: ...
  - Right pedal pressed. Requesting capture start for episodeN.
  - Capture started successfully: episodeN
  - Right pedal pressed. Requesting capture stop.
  - Capture stopped successfully.

  如果你想看录制本体是否真的在写数据，就看终端 5。
  另外也可以随时检查目录：

  ls -d $HOME/agilex/data/episode*

  如果你要更稳一点，我建议你在开始正式录之前先确认脚踏板设备路径存在：

  ls -l /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd

  如果你愿意，我可以下一条直接给你整理成一个“s1-s6 一行一行照抄”的完整清单。










  终端 1

  roscore

  终端 2：双 sensor

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  cd ~/pika_ros/scripts
  bash start_multi_sensor.bash sensor

  终端 3：双 gripper

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  cd ~/pika_ros/scripts
  bash start_multi_gripper.bash gripper sensor

  终端 4：双臂 teleop

  conda activate pika
  source ~/pika_ros/install/setup.zsh
  roslaunch pika_remote_piper teleop_rand_multi_piper.launch

  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh bash /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash
  tmux attach -t piper-dual-low

# 终端5:数据采集
source ~/pika_ros/install/setup.bash 
roslaunch data_tools run_data_capture.launch type:=single_pika datasetDir:=$HOME/agilex/data episodeIndex:=0  # 单夹持器
roslaunch data_tools run_data_capture.launch type:=single_pika_teleop datasetDir:=$HOME/agilex/data episodeIndex:=0  # 单夹持器遥操作

source ~/pika_ros/install/setup.bash 
roslaunch data_tools run_data_capture.launch type:=multi_pika datasetDir:=$HOME/agilex/data episodeIndex:=0  # 双夹持器
roslaunch data_tools run_data_capture.launch type:=multi_pika_teleop datasetDir:=$HOME/agilex/data episodeIndex:=0  # 双夹持器遥操作

roslaunch data_tools run_data_capture.launch useService:=true type:=single_pika datasetDir:=$HOME/agilex/data episodeIndex:=0  # 单夹持器
roslaunch data_tools run_data_capture.launch useService:=true type:=single_pika_teleop datasetDir:=$HOME/agilex/data episodeIndex:=0  # 单夹持器遥操作


source ~/pika_ros/install/setup.bash 
roslaunch data_tools run_data_capture.launch useService:=true type:=multi_pika datasetDir:=$HOME/agilex/data episodeIndex:=0  # 双夹持器
roslaunch data_tools run_data_capture.launch useService:=true type:=multi_pika_teleop datasetDir:=$HOME/agilex/data episodeIndex:=0  # 双夹持器遥操作


rosservice call /teleop_trigger_l "{}"
rosservice call /teleop_trigger_r "{}"


  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh

  roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
    serial_no:=817412070803 \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=1 \
    useService:=true
  
  # S5
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh

  roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
    serial_no:=817412070803 \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=7 \
    useService:=true


  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh

  LAST_EPISODE=$(find "$HOME/agilex/data" -maxdepth 1 -type d -name 'episode*' -printf '%f\n' 2>/dev/null | sed 's/^episode//' | sort -n |
  tail -1)
  NEXT_EPISODE=${LAST_EPISODE:-0}
  NEXT_EPISODE=$((NEXT_EPISODE + 1))

  roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
    serial_no:=817412070803 \
    datasetDir:=$HOME/agilex/data \
    episodeIndex:=$NEXT_EPISODE \
    useService:=true


  终端 5：

  # conda deactivate
  # export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  # unset PYTHONHOME
  # unset PYTHONPATH
  # source /opt/ros/noetic/setup.zsh
  # source ~/pika_ros/install/setup.zsh
  # roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
  #   serial_no:=817412070803 \
  #   datasetDir:=$HOME/agilex/data \
  #   episodeIndex:=0 \
  #   useService:=true
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

  终端 6：

  # bash ~/pika_ros/scripts/start_dual_teleop_capture_sync.bash $HOME/agilex/data
  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
   sudo /usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py --dataset-dir $HOME/agilex/data


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

  终端 6：启动脚踏板采集控制

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data


    如果你想自己指定输出路径：

  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 4 \
    --output ~/agilex/data/episode4/camera_overview_custom.mp4

  如果你想把 depth 目录里有图的相机也一起拼进去：

  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 4 --include-depth

  如果你只想拼指定几个相机，比如 D435 加左右 gripper 彩色：

  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 7 \
    --only myD435 pikaGripperDepthCamera_l pikaGripperDepthCamera_r

  常用可调参数还有：

  --fps 20
  --tile-width 640
  --tile-height 480
  --max-gap 0.25


  # 可视化视频（图片拼接）
  # 单个 episode：

  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 4

  # 全部 episode：

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py

# 监控d435
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  roslaunch realsense2_camera rs_camera.launch serial_no:=817412070803

  再看另一个终端：

  rostopic hz /camera/color/image_raw



  # 10hz限制去除
    终端 5，用新的严格版 s5：

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_s5_pedal_strict_capture.bash $HOME/agilex/data

  终端 6，继续用现有脚踏板 s6：

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  sudo -E bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data



# 10hz
  新命令这样用，原来的不改：

  s5：

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash task_demo

  s6：

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash task_demo

  运行后日志会写到 ~/agilex/task_demo：

  - foot_pedal_capture.log
  - capture_service.log
  - capture_service_requests.log
  - capture_status_hz_buffered_10hz.log
  - buffered_capture_relay_10hz.log

  我还把可视化脚本补成支持任务名了：

  - 单个 episode：

  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 3 --task-name task_demo

  - 全部 episode：

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name task_demo
  --overwrite

  - hz 分析：

  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 --task-name task_demo

  补充：

  - 这次没有把你当前未提交的 pika_ros/pipline.sh 和 usage.sh 改动带进提交。
  - 现在工作区剩余未提交的只有这两个文件。


    source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  /usr/bin/python3 ~/pika_ros/scripts/record_named_robot_pose.py --name my_init_pose


  sudo systemctl restart gdm3


# 移动
# 模拟
SRC=/home/piper/agilex/pour
DST=/home/piper/agilex/pnp_star_pear
START_FROM=58
next=$(( $(find "$DST" -maxdepth 1 -type d -name 'episode*' -printf '%f\n' | sed 's/episode//' | sort -n | tail -1) + 1 ))
i=$next
for s in $(find "$SRC" -maxdepth 1 -type d -name 'episode*' -printf '%f\n' | sed 's/episode//' | awk -v min="$START_FROM" '$1>=min' | sort -n); do
  echo mv "$SRC/episode$s" "$DST/episode$i"
  i=$((i+1))
done
# 执行
SRC=/home/piper/agilex/pour
DST=/home/piper/agilex/pnp_star_pear
START_FROM=58
next=$(( $(find "$DST" -maxdepth 1 -type d -name 'episode*' -printf '%f\n' | sed 's/episode//' | sort -n | tail -1) + 1 ))
i=$next
for s in $(find "$SRC" -maxdepth 1 -type d -name 'episode*' -printf '%f\n' | sed 's/episode//' | awk -v min="$START_FROM" '$1>=min' | sort -n); do
  mv "$SRC/episode$s" "$DST/episode$i"
  i=$((i+1))
done



# 人手数据

 这个版本符合你这次的要求：

  - 不改 s5/s6
  - 只录 D435 的 rgb + depth
  - 只用脚踏板最右边 KEY_C 开始/结束
  - 左、中的踏板完全忽略
  - 数据按 task/episode* 保存

  之所以还是用了 ROS topic，而不是 pyrealsense2 直连，是因为你这台机器当前环境里没有 pyrealsense2，这条路反而更麻烦。现在这个方案是本地最简单、能
  直接跑通的。

  启动方式分两步。

  # 先单独打开 D435，注意这次要开 depth 和对齐：

  # roslaunch realsense2_camera rs_camera.launch \
  #   serial_no:=817412070803 \
  #   camera:=camera \
  #   tf_prefix:=camera \
  #   enable_color:=true \
  #   enable_depth:=true \
  #   align_depth:=true \
  #   enable_pointcloud:=false \
  #   enable_infra:=false \
  #   enable_infra1:=false \
  #   enable_infra2:=false \
  #   color_width:=640 color_height:=480 color_fps:=30 \
  #   depth_width:=640 depth_height:=480 depth_fps:=30

  # # 再开录制脚本：

  # conda deactivate
  # export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  # unset PYTHONHOME
  # unset PYTHONPATH
  # source /opt/ros/noetic/setup.zsh
  # source ~/pika_ros/install/setup.zsh
  # sudo -E /usr/bin/python3 ~/pika_ros/scripts/record_head_d435_rgbd_with_pedal.py --task-name pour_head


# s7：只启动 D435

  roslaunch realsense2_camera rs_camera.launch \
    serial_no:=817412070803 \
    camera:=camera \
    tf_prefix:=camera \
    enable_color:=true \
    enable_depth:=true \
    align_depth:=true \
    enable_pointcloud:=false \
    enable_infra:=false \
    enable_infra1:=false \
    enable_infra2:=false \
    color_width:=640 color_height:=480 color_fps:=30 \
    depth_width:=640 depth_height:=480 depth_fps:=30

  # s8：只启动脚踏板录制器

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh

  sudo -E env PATH="$PATH" LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
  /usr/bin/python3 ~/pika_ros/scripts/record_head_d435_rgbd_with_pedal.py \
    --task-name pour \
    --dataset-root ~/agilex/human \
    --camera-ns camera \
    --rgb-topic /camera/color/image_raw \
    --depth-topic /camera/aligned_depth_to_color/image_raw \
    --rgb-info-topic /camera/color/camera_info \
    --depth-info-topic /camera/aligned_depth_to_color/camera_info \
    --device /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd

  说明：

  - 右脚踏板 KEY_C 按一下开始，再按一下结束
  - 数据保存到 ~/agilex/human/pour/episodeN

  一键启动

  直接用这个：

  bash ~/pika_ros/scripts/start_head_d435_rgbd_pedal.sh pour

  如果你要换任务名，比如 pick_place：

  bash ~/pika_ros/scripts/start_head_d435_rgbd_pedal.sh pick_place

  这个一键脚本会自动：

  - 起 D435
  - 等待 topic 就绪
  - 起脚踏板录制器
  - 保存到 ~/agilex/human/<task_name>/episodeN

  - 相机内参 camera_info.json
  - episode 元信息 head_d435_rgbd_meta.json

  关于 depth 单位：

  - 这个脚本默认按 RealSense 常见格式处理：16UC1 原始深度通常是毫米 mm
  - 同时额外保存一份 *_meters.npy，单位是米 m
  - 所以你既有原始 depth 图，也有精确尺度的米制深度



  # 可视化所有频率
  你可以直接运行（全任务）：
/usr/bin/python3 ~/pika_ros/scripts/analyze_task_episode_hz_minmax.py --task-name pnp_star_pear --skip-missing

你也可以只看部分 episode：
/usr/bin/python3 ~/pika_ros/scripts/analyze_task_episode_hz_minmax.py --task-name pnp_star_pear 120 121 122 --skip-missing


  conda create -n robotwin-data python=3.10 -y && conda activate robotwin-data && conda install -c conda-forge numpy h5py opencv scipy pyyaml -y

#  指定输出目录的命令可以直接用这个：
  python /home/piper/pika_ros/scripts/process_data_robotwin_headcam.py \
    /home/piper/agilex/pnp_star_pear \
    "Pick up the starfruit and the pear, then place them onto the blue plate." \
    160 \
    --output-dir /home/piper/agilex/processed_robotwin/pnp_star_pear-160


  # 内容检查脚本也已经加好了，在 pika_ros/scripts/check_processed_robotwin_headcam.py。用法例子：

  python /home/piper/pika_ros/scripts/check_processed_robotwin_headcam.py \
    /home/piper/agilex/processed_robotwin/pnp_star_pear-50 \
    --episode 0

  # 如果你想连续抽查几个 episode：

  for i in 0 1 2; do
    python /home/piper/pika_ros/scripts/check_processed_robotwin_headcam.py \
      /home/piper/agilex/processed_robotwin/pnp_star_pear-50 \
      --episode $i
  done



rclone copy  /home/piper/agilex/pour gdrive_yzj:piper/pour-blue  -P 

rclone copy  /home/piper/agilex/processed_robotwin/pnp_star_pear-160 gdrive_yzj:piper/pnp_star_pear-129 -P --dry-run

tar -czvf pnp_star_pear-129.tar.gz /home/piper/agilex/processed_robotwin/pnp_star_pear-160
rclone copy  /home/piper/agilex/processed_robotwin/pnp_star_pear-129.tar.gz gdrive_yzj:piper/129-pnp_star_pear/ -P --dry-run



# 解码hdf5中的图片
RGB VS BGR
 - *_decoded.jpg：按 OpenCV 正常解码后的图片
  - *_channel_swapped.jpg：红蓝通道交换后的图片
  - *_compare.jpg：左右对比图，左边是正常解码，右边是红蓝交换

  如果黄色在 channel_swapped 里正常、在 decoded 里不正常，那就是 RGB/BGR 通道顺序问题。

  指定某一帧也可以：

  python /home/piper/pika_ros/scripts/export_robotwin_hdf5_preview_images.py \
    /home/piper/agilex/processed_robotwin/pnp_star_pear-160/episode_0/episode_0.hdf5 \
    --index 0 --index 20 --index -1

  只导出头部相机：

  python /home/piper/pika_ros/scripts/export_robotwin_hdf5_preview_images.py \
    /home/piper/agilex/processed_robotwin/pnp_star_pear-160/episode_0/episode_0.hdf5 \
    --camera cam_high

bash ~/pika_ros/scripts/render_human_episode_videos.sh pnp_star_pear /home/piper/agilex/human