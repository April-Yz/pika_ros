#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-piper-mon}"
SETUP_SCRIPT="${PIKA_ROS_SETUP:-/home/piper/pika_ros/install/setup.bash}"
WORKDIR="/home/piper"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux 未安装"
  exit 1
fi

if [ ! -f "$SETUP_SCRIPT" ]; then
  echo "未找到 setup 脚本: $SETUP_SCRIPT"
  echo "可通过环境变量指定，例如:"
  echo "  PIKA_ROS_SETUP=/home/piper/pika_ros/install/setup.zsh"
  exit 1
fi

run_in_window() {
  local target="$1"
  local command="$2"
  tmux send-keys -t "$target" "cd $WORKDIR && source $SETUP_SCRIPT && $command" C-m
}

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session 已存在: $SESSION_NAME"
  echo "先执行: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

tmux new-session -d -s "$SESSION_NAME" -n summary
run_in_window "$SESSION_NAME:summary" "watch -n 1 'printf \"=== nodes ===\\n\"; rosnode list 2>/dev/null | sort; printf \"\\n=== key topics ===\\n\"; rostopic list 2>/dev/null | rg \"^/(pika_pose|pika_localization_status|teleop_status|arm_control_status|piper_IK/ctrl_end_pose|piper_FK/urdf_end_pose_orient|joint_states_single|joint_states_gripper)$\" || true'"

tmux new-window -t "$SESSION_NAME" -n loc_status
run_in_window "$SESSION_NAME:loc_status" "rostopic echo /pika_localization_status"

tmux new-window -t "$SESSION_NAME" -n teleop_status
run_in_window "$SESSION_NAME:teleop_status" "rostopic echo /teleop_status"

tmux new-window -t "$SESSION_NAME" -n arm_status
run_in_window "$SESSION_NAME:arm_status" "rostopic echo /arm_control_status"

tmux new-window -t "$SESSION_NAME" -n pika_pose
run_in_window "$SESSION_NAME:pika_pose" "rostopic echo /pika_pose"

tmux new-window -t "$SESSION_NAME" -n ctrl_pose
run_in_window "$SESSION_NAME:ctrl_pose" "rostopic echo /piper_IK/ctrl_end_pose"

tmux new-window -t "$SESSION_NAME" -n fk_pose
run_in_window "$SESSION_NAME:fk_pose" "rostopic echo /piper_FK/urdf_end_pose_orient"

tmux new-window -t "$SESSION_NAME" -n joint_in
run_in_window "$SESSION_NAME:joint_in" "rostopic echo /joint_states_single"

tmux new-window -t "$SESSION_NAME" -n joint_out
run_in_window "$SESSION_NAME:joint_out" "rostopic echo /joint_states_gripper"

tmux new-window -t "$SESSION_NAME" -n hz
run_in_window "$SESSION_NAME:hz" "rostopic hz /pika_pose /piper_IK/ctrl_end_pose /joint_states_single /joint_states_gripper"

tmux new-window -t "$SESSION_NAME" -n trigger
run_in_window "$SESSION_NAME:trigger" "printf '手动触发 teleop:\\n  rosservice call /teleop_trigger \"{}\"\\n\\n'; bash"

tmux select-window -t "$SESSION_NAME:summary"
echo "已创建监控 session: $SESSION_NAME"
echo "进入方式: tmux attach -t $SESSION_NAME"
