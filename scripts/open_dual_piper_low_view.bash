#!/usr/bin/env bash

set -euo pipefail

BASE_SESSION="${1:-piper-dual-low}"
VIEW_SESSION="${2:-piper-dual-low-4}"
SETUP_SCRIPT="${PIKA_ROS_SETUP:-/home/piper/pika_ros/install/setup.zsh}"
LOW_SCRIPT="/home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux 未安装"
  exit 1
fi

if ! tmux has-session -t "$BASE_SESSION" 2>/dev/null; then
  bash "$LOW_SCRIPT" "$BASE_SESSION"
fi

if ! tmux has-session -t "$VIEW_SESSION" 2>/dev/null; then
  tmux new-session -d -t "$BASE_SESSION" -s "$VIEW_SESSION"
fi

tmux attach -t "$VIEW_SESSION"
