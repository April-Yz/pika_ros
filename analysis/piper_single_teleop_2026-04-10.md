# Piper Single Teleop Analysis - 2026-04-10

## Scope

User reported:

- `start_sensor_gripper.bash` stage reports many issues.
- gripper motion can synchronize.
- arm position does not synchronize.
- manual `source ~/pika_ros/install/setup.bash` in `zsh` prints `/home/piper/setup.sh` missing.

## Git State Snapshot

Top-level workspace `~/pika_ros` is not clean.

Modified:

- `scripts/setup_device.py`
- `scripts/setup_multi_gripper.bash`
- `scripts/setup_multi_sensor.bash`
- `scripts/setup_sensor_gripper.bash`
- `scripts/start_multi_gripper.bash`
- `scripts/start_multi_sensor.bash`
- `scripts/start_sensor_gripper.bash`
- `scripts/start_single_sensor.bash`

Untracked highlights:

- `.catkin_workspace`
- `build/`
- `devel/`
- `install/`
- `src/PikaAnyArm/`
- several `*.bak` files

Sub-repo `~/pika_ros/src/PikaAnyArm/piper/piper_ros` is clean on `master...origin/master`.

## Confirmed Findings

### 1. `setup.bash` error is a shell mismatch, not the main teleop failure

`~/pika_ros/install/setup.bash` uses `BASH_SOURCE[0]`. When sourced from `zsh`, it resolves relative to the current directory and tries to source `/home/piper/setup.sh`.

Confirmed by file contents:

- `install/setup.bash`
- `install/setup.zsh`

Conclusion:

- in `zsh`, use `source ~/pika_ros/install/setup.zsh`
- in `bash`, use `source ~/pika_ros/install/setup.bash`

### 2. CAN side is not the primary blocker

`teleop_rand_single_piper.launch` starts:

- `piper_ctrl_single_node`
- `piper_FK`
- `piper_IK`
- `teleop_piper`

Observed logs show:

- arm auto-enable changes from `False` to `True`
- `piper_ctrl_single_node` starts normally
- `piper_IK` subscribes to `/piper_IK/ctrl_end_pose`
- `teleop_piper` advertises `/teleop_trigger` and `/teleop_status`

This means the arm-side ROS graph comes up.

### 3. Gripper sync can work even when teleop pose sync is not active

The wiring is:

- `piper_ctrl_single_node` subscribes to `/joint_states_gripper`
- `/joint_states_gripper` is published by `sensor_serial_gripper_imu`
- it merges `/joint_states_single` with the sensor-side gripper distance as joint 7

Therefore:

- gripper motion can synchronize through the topic bridge,
- even if pose teleop has not actually started.

This explains the user symptom: gripper moves, arm position does not.

### 4. Pose teleop depends on two extra conditions

`teleop_piper_publish.py` only publishes `/piper_IK/ctrl_end_pose` when:

- `/teleop_trigger` has toggled teleop state to active
- both initial reference frames are captured:
  - `/pika_pose`
  - `/piper_FK/urdf_end_pose_orient`

If teleop is not active, or if `/pika_pose` is unavailable/unstable, no arm target pose is published.

### 5. Sensor stack has runtime instability

Observed runtime evidence from ROS logs:

- `gripper/camera/realsense2_camera_manager` reports `failed to set power state`
- `sensor_camera_fisheye-3` repeatedly dies and respawns

These errors are consistent with localization instability or degraded sensor input.
If localization is unstable, `/pika_pose` may exist as a topic but still be unusable for teleop.

### 6. Latest live check: teleop target is produced, but IK rejects it

Live ROS checks in the running session showed:

- `/pika_pose` publishes at about 149 Hz
- `/pika_localization_status` reports `accurate: True`
- after calling `rosservice call /teleop_trigger "{}"`, `/teleop_status` publishes `fail: False`, `quit: False`
- `/piper_IK/ctrl_end_pose` publishes continuously
- `/arm_control_status` publishes only `over_limit: True`
- `/joint_states_gripper` does not publish during this state

Interpretation:

- teleop trigger is working
- localization topic exists and is marked accurate
- the arm still does not move because `piper_IK` rejects every target before joint commands are forwarded to `/joint_states_gripper`

### 7. High-confidence code-level risk in IK seeding

`piper_IK.py` subscribes to `/joint_states_single`, but its call into the solver is:

- `self.arm_ik.ik_fun(target.homogeneous, msg.pose.orientation.w)`

It does not pass current joint state as the initial guess, even though `ik_fun()` accepts a `motorstate` argument.

This means the optimizer starts from its internal default state instead of the real current arm configuration.
When the real arm is already away from the nominal pose, the solver can fail or hit self-collision checks even for targets near the current end pose.

Supporting evidence:

- current FK pose and current target pose are nearly identical in Cartesian position and Euler orientation
- despite that, `/arm_control_status` stays `over_limit: True`

This strongly suggests a solver-seeding or collision-check issue, not a missing topic issue.

## High-Probability Root Causes

### A. Teleop trigger was not actually latched on

The code toggles teleop through `/teleop_trigger`, normally driven by a double-click event from `serial_gripper_imu`.
If the double-click is not recognized, the arm will not publish pose commands.

Why this is plausible:

- user sees no arm motion change after launch,
- gripper sync alone does not prove teleop active,
- current logs do not show direct evidence that `/piper_IK/ctrl_end_pose` is receiving live pose messages.

### B. `/pika_pose` localization is unhealthy

The locator node exists, but sensor-side camera failures were logged.
Teleop requires a stable localization pose stream.

Why this is plausible:

- `pika_single_locator` publishes `/pika_pose`,
- but RealSense and fisheye errors were recorded in the same session,
- missing or unstable pose would block arm position sync while leaving gripper sync intact.

### C. IK receives no valid target, or target solving is rejected

`piper_IK.py` rejects solutions when Cartesian error exceeds thresholds:

- `diffX > 0.3`
- `diffY > 0.3`
- `diffZ > 0.3`

If the incoming target pose is bad, stale, or uninitialized, IK can refuse to publish usable arm commands.

### D. IK solver is seeded incorrectly for the real current arm pose

This is now a stronger hypothesis than before.

Why this is plausible:

- `piper_IK.py` has access to `/joint_states_single`
- but does not pass that state into `ik_fun()`
- target pose is close to current FK pose
- yet the solver still reports `over_limit`

This pattern is consistent with solver initialization or self-collision rejection from a bad initial guess.

## Recommended Runtime Checks

Run in the active ROS session after launching both sensor and piper sides:

1. `source ~/pika_ros/install/setup.zsh`
2. `rostopic hz /pika_pose`
3. `rostopic echo -n 1 /pika_localization_status`
4. `rostopic echo -n 1 /teleop_status`
5. manually trigger once: `rosservice call /teleop_trigger "{}"`
6. `rostopic echo -n 3 /piper_IK/ctrl_end_pose`
7. `rostopic echo -n 3 /arm_control_status`
8. `rostopic echo -n 3 /joint_states_gripper`

Interpretation:

- if `/teleop_status` stays fail or quit, teleop never armed
- if `/pika_pose` has no stable output, localization is the blocker
- if `/piper_IK/ctrl_end_pose` stays empty after trigger, teleop publisher is not producing targets
- if `/arm_control_status` reports over-limit, IK is rejecting or clamping targets

## Live Evidence Snapshot

- Current FK pose:
  - position about `x=0.2211, y=-0.0111, z=0.0797`
  - Euler about `roll=0.3821, pitch=0.4028, yaw=-0.0690`
- Current teleop target sample:
  - position about `x=0.2205, y=-0.0109, z=0.0790`
  - Euler fields about `roll=0.3821, pitch=0.4075, yaw=-0.0684`

These values are close, so a persistent `over_limit` is unlikely to be caused by a large Cartesian mismatch alone.

## Relevant Files

- `scripts/start_sensor_gripper.bash`
- `src/sensor_tools/launch/open_sensor_gripper.launch`
- `src/sensor_tools/src/serial_gripper_imu.cpp`
- `src/PikaAnyArm/piper/pika_remote_piper/scripts/teleop_piper_publish.py`
- `src/PikaAnyArm/piper/pika_remote_piper/scripts/piper_IK.py`
- `src/PikaAnyArm/piper/pika_remote_piper/scripts/piper_FK.py`
- `src/PikaAnyArm/piper/piper_ros/piper/scripts/piper_ctrl_single_node.py`

## Relevant Runtime Logs

- `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/roslaunch-Compineter-3194706.log`
- `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/roslaunch-Compineter-3193444.log`
- `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/master.log`
- `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/teleop_piper-4.log`
- `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/rosout.log`

## Documentation And Monitoring Notes

- The low-frequency tmux monitor `piper-low` should be interpreted as:
  - `pose`: current FK pose, current teleop-to-IK target pose, and their difference
  - `gripper`: sense-side gripper opening and merged control opening
  - `status`: localization state, teleop state, and IK over-limit state
  - `trigger`: manual teleop trigger helper

- The correct topic to inspect when asking “what pose IK wants to reach” is:
  - `/piper_IK/ctrl_end_pose`
  - This is an EE pose target, not a joint-angle command.

- The low-frequency monitor was corrected so that CTRL orientation is displayed as true Euler `roll pitch yaw`, matching the FK display and avoiding quaternion-field mislabeling.

## Added Jitter Diagnosis Tooling

To separate localization jitter from teleop/IK jitter and execution jitter, a second set of tools was added:

- `scripts/single_piper_jitter_probe.py`
  - Online 1 Hz probe for:
    - `/pika_pose`
    - `/piper_IK/ctrl_end_pose`
    - `/piper_FK/urdf_end_pose_orient`
    - `/sensor/gripper/joint_state`
    - `/joint_states_single_gripper`
    - `/joint_states_single`
  - Reports message age, estimated frequency, receive-interval jitter, and step size between consecutive frames.

- `scripts/monitor_single_piper_jitter_tmux.bash`
  - tmux launcher combining:
    - pose probe
    - gripper probe
    - raw `rostopic hz`
    - existing low-frequency status monitor
    - a record helper pane

- `scripts/record_single_piper_debug.bash`
  - Records a rosbag plus `rosnode list`, `rostopic list`, and `rostopic info` snapshots for the key topics.

Interpretation guidance encoded in the new doc:

- if `/pika_pose` itself has large step sizes or interval jitter, the likely source is the sense/localization side
- if `/pika_pose` is stable but `/piper_IK/ctrl_end_pose` jumps, the likely source is teleop mapping, trigger state, or IK-side behavior
- if `/piper_IK/ctrl_end_pose` is smooth but `/piper_FK/urdf_end_pose_orient` or `/joint_states_single` is unstable or lagging, the likely source is the execution side

Verification:

- `python3 -m py_compile /home/piper/pika_ros/scripts/single_piper_jitter_probe.py`
- `bash -n /home/piper/pika_ros/scripts/monitor_single_piper_jitter_tmux.bash`
- `bash -n /home/piper/pika_ros/scripts/record_single_piper_debug.bash`

## Repository Hygiene Notes

- A repository-level `.gitignore` was added so routine workspace outputs do not dominate `git status`.
- The ignore rules now cover:
  - `build/`, `devel/`, `install/`
  - Python cache directories and `*.pyc`
  - local `*.bak`
  - rosbag outputs and `logs/jitter_runs/`
  - local third-party source drops under `source/curl-7.75.0/` and `source/librealsense/`

This is intended to keep the working tree focused on source, scripts, docs, and analysis rather than generated artifacts.

## Dual-Arm Runtime Snapshot After Re-Binding

Latest dual-arm checks show a split result:

- serial-side mapping recovered
  - `/dev/ttyUSB50` and `/dev/ttyUSB51` now exist as symlinks
  - `/joint_states_gripper_l` has publisher `/serial_gripper_imu_l`
  - `/joint_states_gripper_r` has publisher `/serial_gripper_imu_r`

- fisheye camera mapping is still wrong
  - `s2` repeatedly reports missing `/dev/video51`
  - current system state does not provide `/dev/video50` or `/dev/video51`
  - current visible symlinks are `/dev/video60 -> video11` and `/dev/video61 -> video22`
  - `sensor_fisheye.rules` still expects:
    - `video50` for `KERNELS=="2-2.2:1.0"`
    - `video51` for `KERNELS=="2-4.2:1.0"`

Interpretation:

- the serial/gripper input path recovered after USB re-binding
- the remaining `s2` failure is now concentrated in fisheye camera udev mapping
- this means the phrase “夹爪没有映射” is no longer accurate for the current snapshot; the serial side is present, but the fisheye side still fails

Dual-arm teleop consequences:

- `s3` nodes for left and right teleop, IK, and FK are up
- `/teleop_trigger_l` and `/teleop_trigger_r` exist
- but reliable dual-arm remote operation still depends on valid left/right pose input and successful per-side triggering
- if one side has broken fisheye/localization input, that side can remain unusable even when joint-state topics exist

Additional tooling added:

- `scripts/lowfreq_dual_piper_monitor.py`
- `scripts/monitor_dual_piper_lowfreq_tmux.bash`
- `docs/tmux双臂遥操监控说明.md`

These provide low-frequency left/right monitoring for:

- `/piper_FK_l/urdf_end_pose_orient`
- `/piper_IK_l/ctrl_end_pose`
- `/piper_FK_r/urdf_end_pose_orient`
- `/piper_IK_r/ctrl_end_pose`
- `/joint_states_gripper_l`
- `/joint_states_gripper_r`
- `/teleop_status_l`
- `/teleop_status_r`
- `/arm_control_status_l`
- `/arm_control_status_r`
## 2026-04-13 Tooling Update

- Added a one-command dual-arm tmux launcher plan:
  - `scripts/start_dual_piper_tmux.bash`
  - Purpose: create independent `s1/s2/s3/s4` tmux sessions and include CAN startup in `s1`.
- Added a detailed dual-arm tmux monitor plan:
  - `scripts/monitor_dual_piper_tmux.bash`
  - Purpose: separate low-frequency summaries from raw localization, target, output, and feedback windows.
- Added a low-frequency linked-view helper:
  - `scripts/open_dual_piper_low_view.bash`
  - Purpose: avoid manual `tmux new-session -t piper-dual-low ...` when viewing different windows in parallel.
- Added a dual-arm tmux cleanup helper:
  - `scripts/cleanup_dual_piper_tmux.bash`
  - Purpose: stop the current dual-arm runtime and monitor tmux sessions before rebuilding them.

Confirmed:

- Existing `piper-jitter`, `piper-low`, and `piper-mon` are single-arm oriented and should not be the default tools for dual-arm debugging.
- The existing `monitor_dual_piper_lowfreq_tmux.bash` remains useful as the lightweight base session for dual-arm work.
- Independent tmux sessions are the correct shape for `s1/s2/s3/s4` because they can be attached in parallel from different terminals without sharing a selected window.

Still a runtime hypothesis:

- Dual-arm failures remain primarily split between right-hand localization quality and teleop state transitions, not launcher absence.

## 2026-04-13 Wait-State Debug Update

Confirmed from live runtime evidence:

- Current left-hand teleop failure is not a CAN-side startup symptom.
- `s4` is stuck printing `wait`, while `s2` simultaneously prints repeated localization volatility warnings.
- Both `/pika_localization_status_l` and `/pika_localization_status_r` were observed as `accurate: False` in the failing run.
- `/pika_pose_l` still publishes a non-zero pose, but `/pika_pose_r` falls back to the zero pose.
- In this state, teleop does not progress to `start` because localization/FK initialization is not considered stable enough.

Implemented debugging support:

- `teleop_piper_publish.py` now prints explicit wait reasons instead of only `wait`.
- The wait diagnostics distinguish:
  - missing initial localization pose latch
  - missing initial FK latch
  - missing `/pika_pose`
  - zero `/pika_pose`
  - missing `/piper_FK/urdf_end_pose_orient`
  - missing `/joint_states_gripper`

Runtime evidence source:

- `tmux capture-pane -pt s4-26`
- `tmux capture-pane -pt s2-2`
- `rostopic echo /pika_localization_status_l`
- `rostopic echo /pika_localization_status_r`
- `rostopic echo /pika_pose_l`
- `rostopic echo /pika_pose_r`

## 2026-04-13 Right-Hand Trigger Follow-up

Confirmed from a later runtime after left teleop recovered:

- `/teleop_trigger_r` does switch `teleop_r` into the active state.
- `/teleop_status_r` stays at `fail=False, quit=False`.
- `/piper_IK_r/ctrl_end_pose`, `/joint_states_r`, `/joint_states_single_r`, and `/arm_control_status_r` all continue to publish.
- The right-hand failure is upstream of IK execution:
  - `/pika_localization_status_r` remains `accurate: False`
  - `/pika_pose_r` remains the zero pose
- This explains why RViz and the right-arm control chain can still show activity while real right-hand teleoperation remains incorrect: downstream nodes are alive, but the teleop input pose is invalid.

Added more debug output:

- While teleop is active, the node now prints warnings when:
  - localization status is inaccurate
  - `/pika_pose` is still the zero pose

Runtime evidence source:

- `tmux capture-pane -pt s4-26`
- `tmux capture-pane -pt s2-2`
- `rostopic echo /teleop_status_r`
- `rostopic echo /pika_localization_status_r`
- `rostopic echo /pika_pose_r`
- `rostopic echo /piper_IK_r/ctrl_end_pose`
- `rostopic echo /joint_states_r`
- `rostopic echo /joint_states_single_r`

## 2026-04-17 Foot Pedal State Snapshot Update

Confirmed in code:

- `scripts/foot_pedal_capture_toggle.py` no longer treats the left pedal as ignored.
- Left pedal `KEY_A` now performs a read-only state snapshot and does not command robot motion.
- The snapshot code looks for current arm joint states on `/joint_states_single`, `/joint_states_single_l`, `/joint_states_single_r`.
- It looks for current FK end pose on `/piper_FK/urdf_end_pose_orient`, `/piper_FK_l/urdf_end_pose_orient`, `/piper_FK_r/urdf_end_pose_orient`.
- It looks for current gripper encoder/state on `/sensor/gripper/data`, `/sensor/gripper_l/data`, `/sensor/gripper_r/data`, `/gripper/gripper/data`, `/gripper/gripper_l/data`, `/gripper/gripper_r/data`.
- If no dedicated `data_msgs/Gripper` topic is available, it falls back to the last joint position from `/joint_states_gripper*` as a derived gripper value.
- Snapshot output is appended to:
  - `datasetDir/foot_pedal_state_snapshot.log`
  - `datasetDir/foot_pedal_state_snapshot.md`

Still only a runtime hypothesis until exercised on the live robot:

- The exact topic subset available in the user's current single-arm or dual-arm launch.
- Whether the preferred gripper data source will be the `data_msgs/Gripper` topic or the fallback last joint in `/joint_states_gripper*`.
- Whether all desired topics publish quickly enough for the current `rospy.wait_for_message(..., timeout=1.0)` window.

Runtime evidence supporting the code-level conclusion:

- source inspection of `scripts/foot_pedal_capture_toggle.py`
- source inspection of `scripts/FOOT_PEDAL.md`
- source inspection of `src/data_msgs/msg/Gripper.msg`
- repository topic references under:
  - `src/data_tools/launch/run_data_capture_multi_pika_teleop_d435.launch`
  - `install/share/pika_remote_piper/scripts/piper_FK.py`
  - `install/share/pika_remote_piper/scripts/teleop_piper_publish.py`

## 2026-04-17 Named Init Pose Capture Update

Confirmed from live runtime evidence:

- A dedicated pose-recording script now exists at `scripts/record_named_robot_pose.py`.
- It writes one named record to both:
  - `docs/robot_named_poses.json`
  - `docs/robot_named_poses.md`
- The record intentionally separates:
  - `joint_state`
  - `fk_pose`
  - `localization_pose`
  - `gripper`
- On the current dual-arm runtime, both arms had:
  - available `/pika_pose_l` and `/pika_pose_r`
  - available `/gripper/gripper_l/data` and `/gripper/gripper_r/data`
  - unavailable live arm joint state on the expected joint topics during the capture window
- Because no arm joint state was available, the current record cannot be used yet as a true joint-space reset/init target.

Current recorded candidate:

- name: `current_init_pose_candidate`
- left localization pose:
  - `x=1.230833, y=-0.266831, z=-0.502442`
- right localization pose:
  - `x=-0.076603, y=-0.138960, z=-0.174994`
- left gripper:
  - `angle=1.663400, distance=0.096391`
- right gripper:
  - `angle=1.670000, distance=0.096707`

Still only a runtime hypothesis:

- The arm joint topics may resume publishing under a different launch mode or only after the arm/control chain is fully active.
- Once a live joint topic becomes available, rerunning `record_named_robot_pose.py` should produce a usable joint-space init candidate and a computed FK pose.

Runtime evidence source:

- `rostopic list`
- `rostopic info /joint_states_single_l`
- `rostopic info /joint_states_single_r`
- `rostopic info /joint_states_gripper_l`
- `rostopic info /joint_states_gripper_r`
- `rostopic info /joint_states_single_gripper_l`
- `rostopic info /joint_states_single_gripper_r`
- `rosnode info /gripper_serial_gripper_imu_l`
- `rosnode info /sensor_serial_gripper_imu_l`
- `rostopic echo -n 1 /gripper/gripper_l/data`
- `rostopic echo -n 1 /gripper/gripper_r/data`
- `rostopic echo -n 1 /pika_pose_l`
- `rostopic echo -n 1 /pika_pose_r`
- `/usr/bin/python3 /home/piper/pika_ros/scripts/record_named_robot_pose.py --name current_init_pose_candidate`
