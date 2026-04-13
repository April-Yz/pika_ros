#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-piper-dual-mon}"
SETUP_SCRIPT="${PIKA_ROS_SETUP:-/home/piper/pika_ros/install/setup.zsh}"
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
  echo "如需重建，请先执行: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

run_window() {
  local target="$1"
  local command="$2"
  tmux send-keys -t "$target" "cd $WORKDIR && export PATH=/usr/bin:/bin:/usr/sbin:/sbin:\$PATH && unset PYTHONHOME && unset PYTHONPATH && source /opt/ros/noetic/setup.zsh && source $SETUP_SCRIPT && $command" C-m
}

tmux new-session -d -s "$SESSION_NAME" -n pose
run_window "$SESSION_NAME:pose" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py pose"

tmux new-window -t "$SESSION_NAME" -n gripper
run_window "$SESSION_NAME:gripper" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py gripper"

tmux new-window -t "$SESSION_NAME" -n status
run_window "$SESSION_NAME:status" "/usr/bin/python3 /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py status"

tmux new-window -t "$SESSION_NAME" -n localization
run_window "$SESSION_NAME:localization" "printf '# 左右定位状态\\n'; rostopic echo /pika_localization_status_l /pika_localization_status_r"

tmux new-window -t "$SESSION_NAME" -n target
run_window "$SESSION_NAME:target" "printf '# 左右目标末端位姿\\n'; rostopic echo /piper_IK_l/ctrl_end_pose /piper_IK_r/ctrl_end_pose"

tmux new-window -t "$SESSION_NAME" -n feedback
run_window "$SESSION_NAME:feedback" "printf '# 左右真实关节反馈\\n'; rostopic echo /joint_states_single_l /joint_states_single_r"

tmux new-window -t "$SESSION_NAME" -n output
run_window "$SESSION_NAME:output" "printf '# 左右关节命令输出\\n'; rostopic echo /joint_states_l /joint_states_r"

tmux new-window -t "$SESSION_NAME" -n hz
run_window "$SESSION_NAME:hz" "rostopic hz /pika_pose_l /pika_pose_r /piper_IK_l/ctrl_end_pose /piper_IK_r/ctrl_end_pose /joint_states_l /joint_states_r /joint_states_single_l /joint_states_single_r"

tmux new-window -t "$SESSION_NAME" -n trigger_l
run_window "$SESSION_NAME:trigger_l" "printf '# 左臂开始或结束遥操\\nrosservice call /teleop_trigger_l \"{}\"\\n'; bash"

tmux new-window -t "$SESSION_NAME" -n trigger_r
run_window "$SESSION_NAME:trigger_r" "printf '# 右臂开始或结束遥操\\nrosservice call /teleop_trigger_r \"{}\"\\n'; bash"

tmux select-window -t "$SESSION_NAME:pose"
echo "已创建双臂详细监控 session: $SESSION_NAME"
echo "进入方式: tmux attach -t $SESSION_NAME"
