# tmux new -t s1

tmux at -t s1
tmux at -t s2


# U1 校准基站
cd ~/pika_ros/install/lib && ./survive-cli --force-calibrate

# 校准手 (不做)
# python3 /home/piper/pika_ros/scripts/setup_device.py --calibrate_base

# 检查相机各类usb can口
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
  
  
# 终端 1
  roscore

# 终端 2：双 sensor
  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  cd ~/pika_ros/scripts
#双击开始采集（会和脚踏板冲突）
#   bash start_multi_sensor.bash sensor
#   若终端 5/6 使用脚踏板采集，请改用下一条；区别：关闭夹爪 Command 的自动采集切换，避免和 s5/s6 冲突
  bash start_multi_sensor_sync_capture.bash sensor

# 终端 3：双 gripper
  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  cd ~/pika_ros/scripts
  # 双击开始采集（会和脚踏板冲突）
  # bash start_multi_gripper.bash gripper sensor
  # 若终端 5/6 使用脚踏板采集，请改用下一条；区别：关闭夹爪 Command 的自动采集切换，避免和 s5/s6 冲突
  bash start_multi_gripper_sync_capture.bash gripper

#终端 4：双臂 teleop
  conda activate pika
  source ~/pika_ros/install/setup.zsh
  roslaunch pika_remote_piper teleop_rand_multi_piper.launch

# # 终端s5
# #   - 启动 D435 的 ROS 节点
# #   - 启动 data_tools_dataCapture 采集服务节点
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
#   roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435.launch \
#     serial_no:=817412070803 \
#     datasetDir:=$HOME/agilex/data \
#     episodeIndex:=0 \
#     useService:=true
# #   终端 6：启动脚踏板采集控制
# #   - 监听脚踏板右踏板 KEY_C
# #   - 按一下就调用 /data_tools_dataCapture/capture_service 开始
# #   - 再按一下就调用同一个服务结束
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
# #   bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data
# #     意思是当前用户没有读这个输入设备的权限。
# #   先临时这样跑：
#   sudo -E bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data
# #   或者直接：
# #   sudo /usr/bin/python3 ~/pika_ros/scripts/foot_pedal_capture_toggle.py --dataset-dir $HOME/agilex/data


# 可视化视频（图片拼接）（非必须）
  # 单个 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 24 25
  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 41
  # 全部 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py  --overwrite
# 可视化结果
 /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 28 


# # 10hz限制去除 debug 版
#     终端 5，用新的严格版 s5：
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
#   bash ~/pika_ros/scripts/start_s5_pedal_strict_capture.bash $HOME/agilex/data

#   终端 6，继续用现有脚踏板 s6：
#   conda deactivate
#   export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
#   unset PYTHONHOME
#   unset PYTHONPATH
#   source /opt/ros/noetic/setup.zsh
#   source ~/pika_ros/install/setup.zsh
#   sudo -E bash ~/pika_ros/scripts/start_foot_pedal_capture_toggle.bash $HOME/agilex/data


#  /home/piper/pika_ros/pipline.sh现在的s123456中有没有指定hz？我看到结果上好像大多数都是30hz？然后
#   realsense有时候会降低到26hz。我需要写一个新的s5 s6，直接不保存鱼眼相机的信息，也不读取，然后维护
#   一个buff，按照10hz的频率保存除了鱼眼相机以外的信息。 2.我想在s5或者s6启动的时候带上任务名称（保
#   存到对应的文件夹中），而不是都在data下面（相当于现在默认都报存在了data任务下面）。 3.对于
#   pipeline中的可视化和统计episode hz的脚本，也需要改成对应的任务名称指定


  s5：
  # conda deactivate
  # export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  # unset PYTHONHOME
  # unset PYTHONPATH
  # source /opt/ros/noetic/setup.zsh
  # source ~/pika_ros/install/setup.zsh
  # bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash pour
# pnp_bread_0512 stack_cup

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash place_bread_basket



  s6:
  # conda deactivate
  # export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  # unset PYTHONHOME
  # unset PYTHONPATH
  # source /opt/ros/noetic/setup.zsh
  # source ~/pika_ros/install/setup.zsh
  # sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash pour


  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash place_bread_basket

pnp_bread 123 6 7 删

  ### 
    # - 单个 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 3 --task-name pour

  # - 全部 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name pour --overwrite
    /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name pour --overwrite

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name pnp_bread --overwrite

  # - hz 分析（单个 episode）：
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 --task-name pour

  # - hz 分析（多个 episode）：
  # /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 4 5 --task-name pour
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour 30 --overwrite

  # - hz 分析（整个任务目录）：
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pnp_star_pear
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pnp_bread

  bash ~/pika_ros/scripts/start_head_d435_rgbd_pedal.sh pnp_star_pear

# RCLONE 同步数据到云盘（待测）
rclone copy  /home/piper/agilex/pour gdrive_yzj:piper/pour-blue  -P # 待测
rclone copy gdrive_yzj:piper/pi0_checkpoints/nsccp/pi05_zaijia_0420piper-129/15000   /home/piper/yzj/ckpt/15000 -P
rclone copy  /home/piper/agilex/human/pnp_star_pear_human.tar.gz gdrive_yzj:piper/human/pnp_star_pear  -P # 待测


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
    --task-name pnp_star_pear \
    --dataset-root ~/agilex/human \
    --camera-ns camera \
    --rgb-topic /camera/color/image_raw \
    --depth-topic /camera/aligned_depth_to_color/image_raw \
    --rgb-info-topic /camera/color/camera_info \
    --depth-info-topic /camera/aligned_depth_to_color/camera_info \
    --device /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd

  # rostopic pub -r 10 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.09,
  # effort: 1.5,
  # velocity: 0.1,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_test_close_slow'}"


  # rostopic pub -r 10 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.04,
  # effort: 1.5,
  # velocity: 0.1,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_test_close_slow'}"



  #   rostopic pub -r 10 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.04,
  # effort: 1.5,
  # velocity: 1.0,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_test_close_fast'}"

  # ### 1. 先测一个明显张开目标

  # 直接发大开，不要发 0.04，发 0.09：

  # rostopic pub -r 10 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.0,
  # effort: 1.5,
  # velocity: 0.2,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_open'}"

  # 同时看反馈：

  # rostopic echo /gripper/gripper_r/data

  # 如果还是一直：

  # distance: 0.0
  # velocity: 0.0
  # effort: 很高

  # 那基本就是执行器本体没动，不是命令方向的问题。

  # ### 2. 再做一次 disable -> enable

  # 先 disable：

  # rostopic pub -1 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.0,
  # effort: 0.0,
  # velocity: 0.0,
  # enable: false,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_disable'}"

  # 再 enable：

  # rostopic pub -1 /sensor/gripper_r/data data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.0,
  # effort: 1.5,
  # velocity: 0.2,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_enable'}"




  # › ### B. sensor 真实反馈

  #     rostopic echo /sensor/gripper_r/data

  #     看这个就知道：

  #     - sensor 手持夹爪自己当前位置是多少
  #     - 它有没有真的执行你发给 /sensor/gripper_r/ctrl 的命令

  #     ### C. gripper 物理夹爪反馈

  #     rostopic echo /gripper/gripper_r/data

  # rostopic pub -r 10 /pi05/gripper_r/ctrl data_msgs/Gripper \
  # "{header: {stamp: now},
  # angle: 0.0,
  # distance: 0.0,
  # effort: 1.5,
  # velocity: 0.2,
  # enable: true,
  # set_zero: false,
  # error: false,
  # voltage: 0.0,
  # driver_temp: 0.0,
  # motor_temp: 0.0,
  # bus_current: 0.0,
  # status: 'manual_open'}"


  /pi05/gripper_r/ctrl


  cd /home/piper/yzj/openpi
/home/piper/.local/bin/uv run python /home/piper/yzj/src/deploy_pi0_piper.py \
  --task-prompt "Pick up the starfruit and the pear, then place them onto the blue plate." \
  --n-iterations 2000 \
  --execute-steps 10 \
  --action-index 0 \
  --left-gripper-clamp-below 0.055 \
  --left-gripper-clamp-to 0.01 \
  --right-gripper-clamp-below 0.065 \
  --right-gripper-clamp-to 0.01 \
  --execution-delay 0.2


# 人手录制流程
# step 1
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

# step 2
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh

sudo -E /usr/bin/python3 ~/pika_ros/scripts/record_head_d435_rgbd_with_pedal.py --task-name pnp_bread

# 人手数据
  bash ~/pika_ros/scripts/render_human_episode_videos.sh pnp_bread /home/piper/agilex/human /home/piper/agilex/human/pnp_bread/videos

