#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TASK_NAME="${1:-}"
DATASET_ROOT="${2:-$HOME/agilex/human}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
OUTPUT_DIR="${3:-$DATASET_ROOT/$TASK_NAME/videos}"

if [[ -z "$TASK_NAME" ]]; then
  echo "Usage: $0 <task_name> [dataset_root]" >&2
  echo "Example: $0 pnp_star_pear" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

dataset_dir="$DATASET_ROOT/$TASK_NAME"
mapfile -t episodes < <(find "$dataset_dir" -maxdepth 1 -type d -name 'episode*' | sort -V)
if [[ ${#episodes[@]} -eq 0 ]]; then
  echo "No episode directories found under $dataset_dir" >&2
  exit 1
fi

for episode_dir in "${episodes[@]}"; do
  episode_name="$(basename "$episode_dir")"
  output_path="$OUTPUT_DIR/${episode_name}.mp4"
  "$PYTHON_BIN" "$SCRIPT_DIR/render_episode_camera_video.py" \
    "$episode_dir" \
    --include-depth \
    --output "$output_path" \
    --overwrite
done
