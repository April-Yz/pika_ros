#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-piper-jitter}"
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

tmux new-session -d -s "$SESSION_NAME" -n pose_probe
run_window "$SESSION_NAME:pose_probe" "/usr/bin/python3 /home/piper/pika_ros/scripts/single_piper_jitter_probe.py pose"

tmux new-window -t "$SESSION_NAME" -n gripper_probe
run_window "$SESSION_NAME:gripper_probe" "/usr/bin/python3 /home/piper/pika_ros/scripts/single_piper_jitter_probe.py gripper"

tmux new-window -t "$SESSION_NAME" -n hz
run_window "$SESSION_NAME:hz" "rostopic hz /pika_pose /piper_IK/ctrl_end_pose /piper_FK/urdf_end_pose_orient /joint_states_single /joint_states_gripper /sensor/gripper/joint_state /joint_states_single_gripper"

tmux new-window -t "$SESSION_NAME" -n status
run_window "$SESSION_NAME:status" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_single_piper_monitor.py status"

tmux new-window -t "$SESSION_NAME" -n record
run_window "$SESSION_NAME:record" "printf '开始录制:\\n  RECORD_SECONDS=60 bash /home/piper/pika_ros/scripts/record_single_piper_debug.bash\\n\\n停止录制: Ctrl-C\\n'; bash"

tmux select-window -t "$SESSION_NAME:pose_probe"
echo "已创建抖动排查 session: $SESSION_NAME"
echo "进入方式: tmux attach -t $SESSION_NAME"
