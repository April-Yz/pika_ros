#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TASK_NAME="${1:-data}"
DATASET_ROOT="${2:-$HOME/agilex}"
SERIAL_NO="${3:-817412070803}"
TASK_DIR="${DATASET_ROOT}/${TASK_NAME}"
CAPTURE_DIR="${TASK_DIR}/unprocessed"

mkdir -p "$TASK_DIR" "$CAPTURE_DIR"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

/usr/bin/python3 "$SCRIPT_DIR/capture_status_hz_logger.py" \
  --dataset-dir "$TASK_DIR" \
  --output-name capture_status_hz_buffered_10hz_no_depth.log &
LOGGER_PID=$!

/usr/bin/python3 "$SCRIPT_DIR/capture_required_topics_warning.py" \
  --dataset-dir "$TASK_DIR" \
  --require-topic /buffered_capture/gripper/camera_l/color/image_raw \
  --require-topic /buffered_capture/gripper/camera_r/color/image_raw \
  --require-topic /buffered_capture/camera/color/image_raw &
WARNING_PID=$!

/usr/bin/python3 "$SCRIPT_DIR/buffered_capture_relay_10hz_no_depth.py" \
  --dataset-dir "$TASK_DIR" \
  --publish-hz 10 &
RELAY_PID=$!

cleanup() {
  kill "$LOGGER_PID" >/dev/null 2>&1 || true
  kill "$WARNING_PID" >/dev/null 2>&1 || true
  kill "$RELAY_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "TASK_NAME=$TASK_NAME"
echo "TASK_DIR=$TASK_DIR"
echo "CAPTURE_DIR=$CAPTURE_DIR"
echo "MODE=buffered_10hz_no_depth"

roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435_buffered_10hz_no_depth.launch \
  serial_no:="$SERIAL_NO" \
  datasetDir:="$CAPTURE_DIR" \
  episodeIndex:=0 \
  useService:=true \
  hz:=-1
