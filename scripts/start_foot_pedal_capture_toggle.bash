#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
DATASET_DIR="${1:-$HOME/agilex/data}"
DEVICE_PATH="${2:-/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd}"
INDEX_ROOT="${3:-$DATASET_DIR}"
LOG_DIR="${4:-$DATASET_DIR}"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

/usr/bin/python3 "$SCRIPT_DIR/foot_pedal_capture_toggle.py" \
  --dataset-dir "$DATASET_DIR" \
  --index-root "$INDEX_ROOT" \
  --log-dir "$LOG_DIR" \
  --device "$DEVICE_PATH"
