#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TASK_NAME="${1:-data}"
DATASET_ROOT="${2:-$HOME/agilex}"
DEVICE_PATH="${3:-/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd}"
DATASET_DIR="${DATASET_ROOT}/${TASK_NAME}"

mkdir -p "$DATASET_DIR"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

echo "TASK_NAME=$TASK_NAME"
echo "DATASET_DIR=$DATASET_DIR"
echo "PEDAL_DEVICE=$DEVICE_PATH"

/usr/bin/python3 "$SCRIPT_DIR/foot_pedal_capture_toggle.py" \
  --dataset-dir "$DATASET_DIR" \
  --device "$DEVICE_PATH"
