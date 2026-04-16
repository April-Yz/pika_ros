#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
DATASET_DIR="${1:-$HOME/agilex/data}"
SERIAL_NO="${2:-817412070803}"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

/usr/bin/python3 "$SCRIPT_DIR/capture_status_hz_logger.py" \
  --dataset-dir "$DATASET_DIR" \
  --output-name capture_status_hz.log &
LOGGER_PID=$!

cleanup() {
  kill "$LOGGER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

roslaunch data_tools run_data_capture_multi_pika_teleop_with_d435_pedal_strict.launch \
  serial_no:="$SERIAL_NO" \
  datasetDir:="$DATASET_DIR" \
  episodeIndex:=0 \
  useService:=true \
  hz:=-1
