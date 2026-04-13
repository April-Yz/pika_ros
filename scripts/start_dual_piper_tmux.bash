#!/usr/bin/env bash

set -euo pipefail

WORKDIR="/home/piper"
PIKA_ROS="/home/piper/pika_ros"
SETUP_ZSH="${PIKA_ROS}/install/setup.zsh"
CAN_DIR="${PIKA_ROS}/src/PikaAnyArm/piper/piper_ros"
PREFIX="${1:-dual}"

S1_SESSION="${PREFIX}-s1"
S2_SESSION="${PREFIX}-s2"
S3_SESSION="${PREFIX}-s3"
S4_SESSION="${PREFIX}-s4"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux 未安装"
  exit 1
fi

if [ ! -f "$SETUP_ZSH" ]; then
  echo "未找到 setup.zsh: $SETUP_ZSH"
  exit 1
fi

create_session() {
  local session="$1"
  local command="$2"
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "tmux session 已存在: $session"
    echo "如需重建，请先执行: tmux kill-session -t $session"
    exit 1
  fi
  tmux new-session -d -s "$session"
  tmux send-keys -t "$session" "$command" C-m
}

create_session "$S1_SESSION" "cd $CAN_DIR && printf '# Step 1 启动机械臂 CAN 通信\\n# Step 2 启动 roscore\\n' && bash can_config.sh && roscore"
create_session "$S2_SESSION" "printf '# Step 3 启动双 sensor 链路\\n'; conda deactivate; export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH; unset PYTHONHOME; unset PYTHONPATH; source /opt/ros/noetic/setup.zsh; source $SETUP_ZSH; cd $PIKA_ROS/scripts; bash start_multi_sensor.bash sensor"
create_session "$S3_SESSION" "printf '# Step 4 启动双 gripper 链路\\n'; conda deactivate; export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH; unset PYTHONHOME; unset PYTHONPATH; source /opt/ros/noetic/setup.zsh; source $SETUP_ZSH; cd $PIKA_ROS/scripts; bash start_multi_gripper.bash gripper sensor"
create_session "$S4_SESSION" "printf '# Step 5 启动双臂 teleop\\n'; conda activate pika; source $SETUP_ZSH; roslaunch pika_remote_piper teleop_rand_multi_piper.launch"

echo "已创建独立双臂启动 sessions:"
echo "  $S1_SESSION"
echo "  $S2_SESSION"
echo "  $S3_SESSION"
echo "  $S4_SESSION"
echo "进入方式示例:"
echo "  tmux attach -t $S1_SESSION"
echo "  tmux attach -t $S2_SESSION"
echo "  tmux attach -t $S3_SESSION"
echo "  tmux attach -t $S4_SESSION"
