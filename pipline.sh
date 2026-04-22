# tmux new -t s1

tmux at -t s1
tmux at -t s2


  # 校准基站

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
#双击开始采集（会和脚踏板冲突）
#   bash start_multi_sensor.bash sensor
#   若终端 5/6 使用脚踏板采集，请改用下一条；区别：关闭夹爪 Command 的自动采集切换，避免和 s5/s6 冲突
  bash start_multi_sensor_sync_capture.bash sensor

  终端 3：双 gripper

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

  终端 4：双臂 teleop

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



# 效果（非必须）
  # 可视化视频（图片拼接）
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

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash pour



  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash pnp_star_pear

  s6：

  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash pour


  conda deactivate
  export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
  unset PYTHONHOME
  unset PYTHONPATH
  source /opt/ros/noetic/setup.zsh
  source ~/pika_ros/install/setup.zsh
  sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash pnp_star_pear



  ### 
    # - 单个 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 3 --task-name pour

  # - 全部 episode：
  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name pour --overwrite

  /usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name pnp_star_pear

  # - hz 分析（单个 episode）：
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 --task-name pour

  # - hz 分析（多个 episode）：
  # /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 4 5 --task-name pour
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour 30 --overwrite

  # - hz 分析（整个任务目录）：
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour
  /usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pnp_star_pear

  bash ~/pika_ros/scripts/start_head_d435_rgbd_pedal.sh pnp_star_pear

# RCLONE 同步数据到云盘（待测）
rclone copy  /home/piper/agilex/pour gdrive_yzj:piper/pour-blue  -P # 待测
rclone copy gdrive_yzj:piper/pi0_checkpoints/nsccp/pi05_zaijia_0420piper-129/15000   /home/piper/yzj/ckpt/15000 -P


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