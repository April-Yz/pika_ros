#!/usr/bin/env bash

set -euo pipefail

PREFIX="${1:-dual}"

SESSIONS=(
  "${PREFIX}-s1"
  "${PREFIX}-s2"
  "${PREFIX}-s3"
  "${PREFIX}-s4"
  "piper-dual-low"
  "piper-dual-low-2"
  "piper-dual-low-3"
  "piper-dual-low-4"
  "piper-dual-low-5"
  "piper-dual-mon"
)

echo "# Step 1 清理双臂运行与监控 tmux"
for session in "${SESSIONS[@]}"; do
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "关闭 session: $session"
    tmux kill-session -t "$session"
  fi
done

echo "# Step 2 当前剩余 tmux sessions"
tmux ls 2>/dev/null || echo "当前没有 tmux session"
