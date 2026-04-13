#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-piper-dual-low}"
SETUP_SCRIPT="${PIKA_ROS_SETUP:-/home/piper/pika_ros/install/setup.bash}"
WORKDIR="/home/piper"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux 未安装"
  exit 1
fi

if [ ! -f "$SETUP_SCRIPT" ]; then
  echo "未找到 setup 脚本: $SETUP_SCRIPT"
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session 已存在: $SESSION_NAME"
  echo "先执行: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

run_window() {
  local target="$1"
  local command="$2"
  tmux send-keys -t "$target" "cd $WORKDIR && export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH && unset PYTHONHOME && unset PYTHONPATH && source $SETUP_SCRIPT && $command" C-m
}

tmux new-session -d -s "$SESSION_NAME" -n pose
run_window "$SESSION_NAME:pose" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py pose"

tmux new-window -t "$SESSION_NAME" -n gripper
run_window "$SESSION_NAME:gripper" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py gripper"

tmux new-window -t "$SESSION_NAME" -n status
run_window "$SESSION_NAME:status" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py status"

tmux new-window -t "$SESSION_NAME" -n trigger_l
run_window "$SESSION_NAME:trigger_l" "printf '左臂触发 teleop:\\n  rosservice call /teleop_trigger_l \"{}\"\\n'; bash"

tmux new-window -t "$SESSION_NAME" -n trigger_r
run_window "$SESSION_NAME:trigger_r" "printf '右臂触发 teleop:\\n  rosservice call /teleop_trigger_r \"{}\"\\n'; bash"

tmux select-window -t "$SESSION_NAME:pose"
echo "已创建双臂低频监控 session: $SESSION_NAME"
echo "进入方式: tmux attach -t $SESSION_NAME"
