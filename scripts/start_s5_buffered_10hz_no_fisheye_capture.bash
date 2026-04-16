#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TASK_NAME="${1:-data}"
DATASET_ROOT="${2:-$HOME/agilex}"
SERIAL_NO="${3:-817412070803}"
DATASET_DIR="${DATASET_ROOT}/${TASK_NAME}"

mkdir -p "$DATASET_DIR"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

/usr/bin/python3 "$SCRIPT_DIR/capture_status_hz_logger.py" \
  --dataset-dir "$DATASET_DIR" \
  --output-name capture_status_hz_buffered_10hz.log &
LOGGER_PID=$!

/usr/bin/python3 "$SCRIPT_DIR/buffered_capture_relay_10hz.py" \
  --dataset-dir "$DATASET_DIR" \
  --publish-hz 10 &
RELAY_PID=$!

cleanup() {
  kill "$LOGGER_PID" >/dev/null 2>&1 || true
  kill "$RELAY_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "TASK_NAME=$TASK_NAME"
echo "DATASET_DIR=$DATASET_DIR"
echo "MODE=buffered_10hz_no_fisheye"

roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435_buffered_10hz_no_fisheye.launch \
  serial_no:="$SERIAL_NO" \
  datasetDir:="$DATASET_DIR" \
  episodeIndex:=0 \
  useService:=true \
  hz:=-1
