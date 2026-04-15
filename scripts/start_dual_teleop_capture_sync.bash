#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
DATASET_DIR="${1:-$HOME/agilex/data}"
INSTRUCTIONS="${2:-[null]}"
STABLE_SEC="${3:-0.3}"

source /opt/ros/noetic/setup.bash
source "$SCRIPT_DIR/../install/setup.bash"

/usr/bin/python3 "$SCRIPT_DIR/dual_teleop_capture_sync.py" \
  --dataset-dir "$DATASET_DIR" \
  --instructions "$INSTRUCTIONS" \
  --stable-sec "$STABLE_SEC"
