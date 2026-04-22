# Buffered 10Hz No-Fisheye Capture

## Purpose

This is a new `s5/s6` workflow for dual-arm capture with these constraints:

- do not subscribe to fisheye camera image topics
- do not save fisheye camera data
- keep the original `s1-s4` commands unchanged
- save non-fisheye topics through a latest-message buffer at `10 Hz`
- allow task-specific dataset directories instead of always writing into `~/agilex/data`

## Current Hz Behavior In Existing Pipeline

Current `pipline.sh` behavior:

- `s1-s4` do not set a capture `hz` threshold in the shell commands themselves
- standard `s5` uses `run_data_capture_multi_pika_teleop_with_d435.launch`
- that launch passes through to `run_data_capture_multi_pika_teleop_d435.launch`
- that capture launch defaults to `hz=20`

Important:

- in `data_tools_dataCapture`, `hz` is a low-frequency failure threshold
- it is **not** the actual data save rate
- RealSense cameras usually target `30 FPS`, but actual runtime rates can drift lower, such as `26 Hz`

## New Workflow

New `s5` and `s6` are added without replacing the original ones.

### New S5

File:

- `scripts/start_s5_buffered_10hz_no_fisheye_capture.bash`

Behavior:

- computes `DATASET_DIR=$DATASET_ROOT/$TASK_NAME`
- starts `capture_status_hz_logger.py`
- starts `buffered_capture_relay_10hz.py`
- starts D435 ROS node
- starts `data_tools_dataCapture`
- capture threshold is disabled with `hz=-1`
- actual saved stream rate is controlled by the relay publisher at `10 Hz`

### New S6

File:

- `scripts/start_s6_buffered_10hz_no_fisheye_capture.bash`

Behavior:

- computes the same task dataset directory
- listens to the foot pedal
- right pedal toggles capture start and stop

## Buffered Topics

The relay subscribes to the original non-fisheye topics and republishes them at `10 Hz`:

- `/gripper/camera_l/color/image_raw`
- `/gripper/camera_r/color/image_raw`
- `/camera/color/image_raw`
- `/gripper/camera_l/aligned_depth_to_color/image_raw`
- `/gripper/camera_r/aligned_depth_to_color/image_raw`
- `/joint_states_gripper_l`
- `/joint_states_gripper_r`
- `/joint_states_single_gripper_l`
- `/joint_states_single_gripper_r`
- `/piper_IK_l/receive_end_pose_orient`
- `/piper_IK_r/receive_end_pose_orient`
- `/piper_FK_l/urdf_end_pose_orient`
- `/piper_FK_r/urdf_end_pose_orient`
- `/pika_pose_l`
- `/pika_pose_r`
- `/sensor/gripper_l/data`
- `/sensor/gripper_r/data`
- `/gripper/gripper_l/data`
- `/gripper/gripper_r/data`

Fisheye topics are excluded from this new capture path.

## Commands

Assume `s1-s4` are already started.

### New S5

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash task_demo
```

This writes episodes under:

```bash
~/agilex/task_demo
```

If you want to keep the old location style, use task name `data`:

```bash
bash ~/pika_ros/scripts/start_s5_buffered_10hz_no_fisheye_capture.bash data
```

### New S6

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
source /opt/ros/noetic/setup.zsh
source ~/pika_ros/install/setup.zsh
sudo -E bash ~/pika_ros/scripts/start_s6_buffered_10hz_no_fisheye_capture.bash task_demo
```

## Logs

These logs are written under the task dataset directory.

- `foot_pedal_capture.log`
  pedal press, capture start request, capture stop request
- `capture_service.log`
  capture service start/stop records
- `capture_service_requests.log`
  who called the capture service
- `capture_status_hz_buffered_10hz.log`
  `data_tools_dataCapture/status` stream during capture
- `buffered_capture_relay_10hz.log`
  source hz and publish hz from the 10 Hz relay
- `episodeN/capture_timing.log`
  actual capture lifetime and frame summary
- `episodeN/statistic.txt`
  capture statistics written by `data_tools_dataCapture`

## Visualization And Hz Analysis With Task Name

Single episode video rendering:

```bash
/usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 3 --task-name task_demo
```

Render all episodes under a task:

```bash
/usr/bin/python3 ~/pika_ros/scripts/render_all_episode_videos.py --task-name task_demo --overwrite
```

Analyze one episode hz summary under a task:

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py 3 --task-name task_demo
```

If the task uses the new buffered workflow, `analyze_episode_hz.py` will automatically prefer:

- `capture_status_hz_buffered_10hz.log`

over the older:

- `capture_status_hz.log`

## Difference From Existing S5/S6

Existing standard `s5`:

- still captures fisheye topics if configured
- still uses the old topic set
- still defaults to `hz=20`

New buffered `s5/s6`:

- no fisheye image capture
- no fisheye topic subscription inside `data_tools_dataCapture`
- save path can be isolated by task name
- buffered non-fisheye save stream at `10 Hz`
- runtime hz logs are recorded for later inspection
