#!/usr/bin/env bash

set -euo pipefail

SETUP_SCRIPT="${PIKA_ROS_SETUP:-/home/piper/pika_ros/install/setup.bash}"
OUT_ROOT="${PIKA_DEBUG_ROOT:-/home/piper/pika_ros/logs/jitter_runs}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$OUT_ROOT/$STAMP"
TOPICS=(
  /pika_pose
  /pika_localization_status
  /teleop_status
  /arm_control_status
  /piper_IK/ctrl_end_pose
  /piper_FK/urdf_end_pose_orient
  /joint_states_single
  /joint_states_gripper
  /sensor/gripper/joint_state
  /joint_states_single_gripper
)

mkdir -p "$OUT_DIR"

if [ ! -f "$SETUP_SCRIPT" ]; then
  echo "未找到 setup 脚本: $SETUP_SCRIPT"
  exit 1
fi

cleanup() {
  local code=$?
  if [ -n "${HZ_PID:-}" ] && kill -0 "$HZ_PID" 2>/dev/null; then
    kill "$HZ_PID" 2>/dev/null || true
  fi
  if [ -n "${BAG_PID:-}" ] && kill -0 "$BAG_PID" 2>/dev/null; then
    kill -INT "$BAG_PID" 2>/dev/null || true
    wait "$BAG_PID" 2>/dev/null || true
  fi
  echo "录制目录: $OUT_DIR"
  exit "$code"
}

trap cleanup INT TERM EXIT

export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source "$SETUP_SCRIPT"

{
  echo "timestamp=$STAMP"
  echo "setup_script=$SETUP_SCRIPT"
  echo "host=$(hostname)"
  echo "pwd=$(pwd)"
  printf 'topics=%s\n' "${TOPICS[*]}"
} > "$OUT_DIR/run_meta.txt"

rosnode list | sort > "$OUT_DIR/rosnode_list.txt" 2>&1 || true
rostopic list | sort > "$OUT_DIR/rostopic_list.txt" 2>&1 || true
for topic in "${TOPICS[@]}"; do
  safe_name="${topic#/}"
  safe_name="${safe_name//\//__}"
  rostopic info "$topic" > "$OUT_DIR/topic_info_${safe_name}.txt" 2>&1 || true
done

rostopic hz "${TOPICS[@]}" > "$OUT_DIR/topic_hz.txt" 2>&1 &
HZ_PID=$!

echo "开始录制 rosbag..."
echo "输出目录: $OUT_DIR"
echo "停止方式: Ctrl-C"

if [ -n "${RECORD_SECONDS:-}" ]; then
  timeout "$RECORD_SECONDS" rosbag record -O "$OUT_DIR/single_piper_debug.bag" "${TOPICS[@]}" &
  BAG_PID=$!
  wait "$BAG_PID"
else
  rosbag record -O "$OUT_DIR/single_piper_debug.bag" "${TOPICS[@]}" &
  BAG_PID=$!
  wait "$BAG_PID"
fi
