#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TASK_NAME="${1:-}"
SERIAL_NO="${2:-817412070803}"
CAMERA_NS="${3:-camera}"
DATASET_ROOT="${4:-$HOME/agilex/human}"
PEDAL_DEVICE="${5:-/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd}"

if [[ -z "$TASK_NAME" ]]; then
  echo "Usage: $0 <task_name> [serial_no] [camera_ns] [dataset_root] [pedal_device]" >&2
  exit 1
fi

export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

DATASET_DIR="${DATASET_ROOT}/${TASK_NAME}"
mkdir -p "$DATASET_DIR"

cleanup() {
  if [[ -n "${ROSLAUNCH_PID:-}" ]]; then
    kill "$ROSLAUNCH_PID" >/dev/null 2>&1 || true
    wait "$ROSLAUNCH_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "TASK_NAME=$TASK_NAME"
echo "DATASET_DIR=$DATASET_DIR"
echo "SERIAL_NO=$SERIAL_NO"
echo "CAMERA_NS=$CAMERA_NS"
echo "PEDAL_DEVICE=$PEDAL_DEVICE"

roslaunch realsense2_camera rs_camera.launch \
  serial_no:="$SERIAL_NO" \
  camera:="$CAMERA_NS" \
  tf_prefix:="$CAMERA_NS" \
  enable_color:=true \
  enable_depth:=true \
  align_depth:=true \
  enable_pointcloud:=false \
  enable_infra:=false \
  enable_infra1:=false \
  enable_infra2:=false \
  color_width:=640 \
  color_height:=480 \
  color_fps:=30 \
  depth_width:=640 \
  depth_height:=480 \
  depth_fps:=30 \
  >"${DATASET_DIR}/realsense_launch.log" 2>&1 &
ROSLAUNCH_PID=$!

for _ in $(seq 1 30); do
  if rostopic type "/${CAMERA_NS}/color/image_raw" >/dev/null 2>&1 && \
     rostopic type "/${CAMERA_NS}/aligned_depth_to_color/image_raw" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! rostopic type "/${CAMERA_NS}/color/image_raw" >/dev/null 2>&1; then
  echo "Failed to detect /${CAMERA_NS}/color/image_raw" >&2
  exit 1
fi

if ! rostopic type "/${CAMERA_NS}/aligned_depth_to_color/image_raw" >/dev/null 2>&1; then
  echo "Failed to detect /${CAMERA_NS}/aligned_depth_to_color/image_raw" >&2
  exit 1
fi

sudo -E env \
  PATH="$PATH" \
  LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}" \
  /usr/bin/python3 "$SCRIPT_DIR/record_head_d435_rgbd_with_pedal.py" \
    --task-name "$TASK_NAME" \
    --dataset-root "$DATASET_ROOT" \
    --camera-ns "$CAMERA_NS" \
    --rgb-topic "/${CAMERA_NS}/color/image_raw" \
    --depth-topic "/${CAMERA_NS}/aligned_depth_to_color/image_raw" \
    --rgb-info-topic "/${CAMERA_NS}/color/camera_info" \
    --depth-info-topic "/${CAMERA_NS}/aligned_depth_to_color/camera_info" \
    --device "$PEDAL_DEVICE"
