#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-piper-dual-run}"
WORKDIR="/home/piper"
PIKA_ROS="/home/piper/pika_ros"
SETUP_ZSH="${PIKA_ROS}/install/setup.zsh"
CAN_DIR="${PIKA_ROS}/src/PikaAnyArm/piper/piper_ros"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux 未安装"
  exit 1
fi

if [ ! -f "$SETUP_ZSH" ]; then
  echo "未找到 setup.zsh: $SETUP_ZSH"
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session 已存在: $SESSION_NAME"
  echo "如需重建，请先执行: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

run_window() {
  local target="$1"
  local command="$2"
  tmux send-keys -t "$target" "$command" C-m
}

tmux new-session -d -s "$SESSION_NAME" -n s1
run_window "$SESSION_NAME:s1" "cd $CAN_DIR && printf '# Step 1 启动机械臂 CAN 通信\\n# Step 2 启动 roscore\\n' && bash can_config.sh && roscore"

tmux new-window -t "$SESSION_NAME" -n s2
run_window "$SESSION_NAME:s2" "printf '# Step 3 启动双 sensor 链路\\n'; conda deactivate; export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH; unset PYTHONHOME; unset PYTHONPATH; source /opt/ros/noetic/setup.zsh; source $SETUP_ZSH; cd $PIKA_ROS/scripts; bash start_multi_sensor.bash sensor"

tmux new-window -t "$SESSION_NAME" -n s3
run_window "$SESSION_NAME:s3" "printf '# Step 4 启动双 gripper 链路\\n'; conda deactivate; export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH; unset PYTHONHOME; unset PYTHONPATH; source /opt/ros/noetic/setup.zsh; source $SETUP_ZSH; cd $PIKA_ROS/scripts; bash start_multi_gripper.bash gripper sensor"

tmux new-window -t "$SESSION_NAME" -n s4
run_window "$SESSION_NAME:s4" "printf '# Step 5 启动双臂 teleop\\n'; conda activate pika; source $SETUP_ZSH; roslaunch pika_remote_piper teleop_rand_multi_piper.launch"

tmux select-window -t "$SESSION_NAME:s1"
echo "已创建双臂启动 session: $SESSION_NAME"
echo "进入方式: tmux attach -t $SESSION_NAME"
