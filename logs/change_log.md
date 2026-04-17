# Change Log

## 2026-04-10

- Added `AGENT-READ.md`.
  - Reason: enforce future debugging discipline for this workspace.
  - Evidence source: user explicitly requested an `agent-read` file and required change logging plus analysis recording.

- Added `analysis/piper_single_teleop_2026-04-10.md`.
  - Reason: record the current diagnosis for single-arm piper teleop with sensor+gripper setup.
  - Evidence source:
    - git status from `~/pika_ros` and `~/pika_ros/src/PikaAnyArm/piper/piper_ros`
    - ROS logs under `/home/piper/.ros/log/8322e2ba-34bd-11f1-b02f-c9c9e99447b8/`
    - source inspection of launch scripts and teleop-related nodes

- No functional control code was changed in this pass.
  - Reason: current evidence points to runtime graph, trigger, or localization issues more strongly than to a confirmed source-code defect.

- Added `scripts/monitor_single_piper_tmux.bash`.
  - Reason: provide a repeatable tmux-based monitor for the single-piper teleop chain.
  - Evidence source: user requested a bash tool that opens multiple tmux monitors for the necessary ROS topics.

- Updated `analysis/piper_single_teleop_2026-04-10.md` with live runtime findings.
  - Reason: latest live checks showed teleop trigger success, active `/piper_IK/ctrl_end_pose`, persistent `/arm_control_status: over_limit`, and no `/joint_states_gripper` output.
  - Evidence source:
    - `tmux capture-pane -pt s2-2:0.0 -S -200`
    - `tmux capture-pane -pt s3-3:0.0 -S -200`
    - `rostopic hz /pika_pose`
    - `rostopic echo /pika_localization_status`
    - `rosservice call /teleop_trigger "{}"`
    - `rostopic echo /teleop_status`
    - `rostopic echo /piper_IK/ctrl_end_pose`
    - `rostopic echo /arm_control_status`

- Added `docs/tmux单臂遥操监控说明.md`.
  - Reason: user requested a Chinese explanation of how to read the tmux monitoring windows.
  - Evidence source: current tmux monitoring layout created by `scripts/monitor_single_piper_tmux.bash`.

- Added `scripts/monitor_single_piper_lowfreq_tmux.bash`.
  - Reason: user requested low-frequency coordinate/state output that is easier to read than raw high-rate `rostopic echo`.
  - Evidence source:
    - current key topics are `/piper_FK/urdf_end_pose_orient`, `/piper_IK/ctrl_end_pose`, `/sensor/gripper/joint_state`, `/joint_states_single_gripper`, `/teleop_status`, `/arm_control_status`, `/pika_localization_status`

- Added `scripts/lowfreq_single_piper_monitor.py`.
  - Reason: provide a stable low-frequency ROS subscriber backend for tmux windows instead of relying on multi-line shell here-doc commands.
  - Evidence source: initial tmux low-frequency script exited immediately and required a more robust implementation.

- Added `docs/执行脚本简明说明.md`.
  - Reason: user requested a simple document that records the execution commands and explains the `yaml` missing-module startup issue.
  - Evidence source:
    - `tmux capture-pane -pt s2-2:0.0 -S -240`
    - confirmed `python3` from conda lacks `yaml`
    - confirmed `/usr/bin/python3` contains `yaml`

- Updated `scripts/monitor_single_piper_lowfreq_tmux.bash`.
  - Reason: `piper-low` tmux panes were starting under conda base and failing to import `yaml` through `rospy`.
  - Evidence source:
    - `tmux capture-pane -pt piper-low:0.0 -S -120`
    - `tmux capture-pane -pt piper-low:1.0 -S -120`
    - `tmux capture-pane -pt piper-low:2.0 -S -120`
    - confirmed `python3` in conda lacks `yaml`, while `/usr/bin/python3` works

- Updated `scripts/lowfreq_single_piper_monitor.py`.
  - Reason: low-frequency `pose` window labeled CTRL orientation as `rpy`, but it was printing quaternion `x y z` fields; changed it to true Euler `roll pitch yaw`.
  - Evidence source: source inspection of the `cb_ctrl()` path in the low-frequency monitor script.

- Updated `docs/tmux单臂遥操监控说明.md`.
  - Reason: user requested that the low-frequency monitor logic, IK target interpretation, and the normal roles of `s2` and `s3` be added to the Chinese tmux documentation.
  - Evidence source:
    - current tmux monitor scripts
    - inspected topic flow for `/pika_pose`, `/piper_IK/ctrl_end_pose`, `/piper_FK/urdf_end_pose_orient`, `/joint_states_single`, `/joint_states_gripper`

- Added `scripts/single_piper_jitter_probe.py`.
  - Reason: provide an online low-frequency probe for distinguishing input-side jitter, teleop/IK-side jitter, and execution-side jitter.
  - Evidence source:
    - active topics `/pika_pose`, `/piper_IK/ctrl_end_pose`, `/piper_FK/urdf_end_pose_orient`, `/joint_states_single`, `/joint_states_gripper`, `/sensor/gripper/joint_state`, `/joint_states_single_gripper`
    - user requested a direct way to analyze which segment introduces delay or shaking

- Added `scripts/monitor_single_piper_jitter_tmux.bash`.
  - Reason: provide a tmux-based, more intuitive online jitter monitor that combines the new probe, frequency view, and status view.
  - Evidence source: user explicitly asked for a more direct observation method.

- Added `scripts/record_single_piper_debug.bash`.
  - Reason: provide a simple recording script that saves a rosbag plus topic metadata for later delay/jitter analysis.
  - Evidence source: user requested a startup script that records key topics for later analysis.

- Added `docs/单臂遥操抖动排查说明.md`.
  - Reason: explain how to use the new online and offline tools and how to decide whether the issue is in localization, teleop mapping, or execution.
  - Evidence source: current single-arm topic graph and the user request for a practical troubleshooting method.

- Verified syntax and executability for the new debugging tools.
  - Evidence source:
    - `python3 -m py_compile /home/piper/pika_ros/scripts/single_piper_jitter_probe.py`
    - `bash -n /home/piper/pika_ros/scripts/monitor_single_piper_jitter_tmux.bash`
    - `bash -n /home/piper/pika_ros/scripts/record_single_piper_debug.bash`

- Updated `.gitignore`.
  - Reason: keep ROS generated outputs, Python caches, local backup files, rosbag recordings, and third-party source drops out of routine status and commits.
  - Evidence source:
    - `git -C /home/piper/pika_ros status --short --branch`
    - `git -C /home/piper/pika_ros check-ignore -v build devel install logs/jitter_runs scripts/__pycache__ scripts/start_sensor_gripper.bash.bak scripts/setup_device.py.bak`

- Updated `AGENT-READ.md`.
  - Reason: enforce a standing workflow rule that every future modification must be logged, reflected in analysis, checked against `.gitignore`, and committed to Git.
  - Evidence source: user explicitly requested a repository rule for future changes and commit discipline.

- Added `scripts/lowfreq_dual_piper_monitor.py`.
  - Reason: provide a low-frequency dual-arm monitor for left/right FK, CTRL, gripper, and teleop status without changing runtime code.
  - Evidence source: user requested a dual-hand version of the existing monitor tooling.

- Added `scripts/monitor_dual_piper_lowfreq_tmux.bash`.
  - Reason: launch the dual-arm low-frequency monitor in tmux with dedicated left/right trigger panes.
  - Evidence source: user requested startup instructions for a dual-hand monitor.

- Added `docs/tmux双臂遥操监控说明.md`.
  - Reason: document how to read the dual-arm monitor and how to distinguish left/right failures.
  - Evidence source: current dual-arm topic graph and user request.

- Recorded latest dual-arm runtime diagnosis in analysis.
  - Reason: after re-binding USB, serial mapping recovered but fisheye camera mapping still points to missing `/dev/video50` and `/dev/video51`.
  - Evidence source:
    - `tmux capture-pane -pt s2-2:0.0 -S -260`
    - `ls -l /dev/ttyUSB* /dev/video50 /dev/video51`
    - `cat /etc/udev/rules.d/sensor_fisheye.rules`
    - `v4l2-ctl --list-devices`
    - `rostopic info /joint_states_gripper_l`
    - `rostopic info /joint_states_gripper_r`

- Verified syntax and executability for the dual-arm monitor tools.
  - Evidence source:
    - `python3 -m py_compile /home/piper/pika_ros/scripts/lowfreq_dual_piper_monitor.py`
    - `bash -n /home/piper/pika_ros/scripts/monitor_dual_piper_lowfreq_tmux.bash`

- Updated the dual-arm monitor to match the four-terminal runtime workflow.
  - Reason: user clarified that the intended dual-arm setup runs both `start_multi_sensor.bash sensor` and `start_multi_gripper.bash gripper sensor`, so the monitor needed to distinguish sensor-side gripper control from gripper-device-side output.
  - Evidence source:
    - source inspection of `open_multi_sensor.launch`
    - source inspection of `open_multi_gripper.launch`
    - runtime topic naming for `/joint_states_gripper_l/r` and `/joint_states_single_gripper_l/r`

- Added `scripts/start_dual_piper_tmux.bash`.
  - Reason: user requested a one-command tmux launcher that creates and runs `s1/s2/s3/s4`, including CAN startup before `roscore`.
  - Evidence source:
    - current dual-arm startup workflow from the user
    - source inspection of `src/PikaAnyArm/piper/piper_ros/can_config.sh`

- Added `scripts/monitor_dual_piper_tmux.bash`.
  - Reason: user requested a more detailed dual-arm monitor beyond the low-frequency summary view.
  - Evidence source:
    - current dual-arm topic graph for localization, target pose, command output, and joint feedback

- Added `scripts/open_dual_piper_low_view.bash`.
  - Reason: user requested a simple way to open another `piper-dual-low` tmux view without manually creating linked sessions.
  - Evidence source:
    - current tmux behavior where multiple clients attached to the same session share the selected window

- Updated `docs/tmux双臂遥操监控说明.md`.
  - Reason: document the new one-command low-view flow, the detailed dual-arm monitor, and clarify that older single-arm tmux sessions are not the recommended tools for dual-arm debugging.
  - Evidence source:
    - current monitor scripts under `scripts/`

- Updated `scripts/start_dual_piper_tmux.bash`.
  - Reason: user asked for `s1/s2/s3/s4` to be independent so they can be opened simultaneously in different terminals.
  - Evidence source:
    - prior implementation created one tmux session with four windows
    - tmux window selection sharing is not appropriate for the requested workflow

- Added `scripts/cleanup_dual_piper_tmux.bash`.
  - Reason: user requested a simple cleanup helper for the dual-arm runtime and monitor tmux sessions.
  - Evidence source:
    - current set of dual-arm runtime sessions and monitor sessions under tmux

- Updated `docs/tmux双臂遥操监控说明.md` again.
  - Reason: document that `start_dual_piper_tmux.bash` now creates independent sessions and add the cleanup command.
  - Evidence source:
    - current behavior of `scripts/start_dual_piper_tmux.bash`

- Updated `src/PikaAnyArm/piper/pika_remote_piper/scripts/teleop_piper_publish.py`.
  - Reason: user requested concrete debug output while `s4` is stuck in `wait`, instead of only printing the word `wait`.
  - Evidence source:
    - current `s4` pane only prints repeated `wait`
    - current runtime shows localization failures and zero right-hand pose, but the teleop node did not expose that cause

- Updated `install/share/pika_remote_piper/scripts/teleop_piper_publish.py`.
  - Reason: runtime currently launches the installed script, so the same wait-debug output must exist in the active installed copy.
  - Evidence source:
    - live roslaunch uses installed package scripts under `install/share`

- Updated `analysis/piper_single_teleop_2026-04-10.md`.
  - Reason: record the latest dual-arm failure mode where both localization status topics were inaccurate and `s4` remained in `wait`.
  - Evidence source:
    - `tmux capture-pane -pt s4-26`
    - `tmux capture-pane -pt s2-2`
    - `rostopic echo /pika_localization_status_l`
    - `rostopic echo /pika_localization_status_r`
    - `rostopic echo /pika_pose_l`
    - `rostopic echo /pika_pose_r`

- Updated `src/PikaAnyArm/piper/pika_remote_piper/scripts/teleop_piper_publish.py` again.
  - Reason: user requested debugging for the case where right-hand trigger succeeds but right-hand teleoperation still does not work.
  - Evidence source:
    - `/teleop_status_r` showed active state
    - `/pika_localization_status_r` remained inaccurate
    - `/pika_pose_r` remained the zero pose

- Updated `install/share/pika_remote_piper/scripts/teleop_piper_publish.py` again.
  - Reason: keep the active installed runtime copy aligned with the new right-hand debug output.
  - Evidence source:
    - runtime uses installed scripts from `install/share`

- Updated `analysis/piper_single_teleop_2026-04-10.md` again.
  - Reason: record the later right-hand failure mode where trigger succeeded but the teleop input pose stayed invalid.
  - Evidence source:
    - `tmux capture-pane -pt s4-26`
    - `tmux capture-pane -pt s2-2`
    - `rostopic echo /teleop_status_r`
    - `rostopic echo /pika_localization_status_r`
    - `rostopic echo /pika_pose_r`

## 2026-04-17

- Updated `scripts/analyze_episode_hz.py`.
  - Reason: `capture_status_hz_buffered_10hz.log` uses `/buffered_capture/...` topic names, so the episode Hz SVG for buffered datasets such as `pour` could render with no curves and all-`NaN` summaries.
  - Evidence source:
    - `/usr/bin/python3 /home/piper/pika_ros/scripts/analyze_episode_hz.py --task-name pour 30 --overwrite`
    - `/home/piper/agilex/pour/capture_status_hz_buffered_10hz.log`
    - `/home/piper/agilex/pour/episode30/capture_timing.log`

- Added `scripts/ISSUE_LOG_2026-04-17_ANALYZE_EPISODE_HZ.md`.
  - Reason: record the root cause and fix for the empty/left-stacked `hz_summary.svg` output in buffered capture datasets.
  - Evidence source:
    - source inspection of `scripts/analyze_episode_hz.py`
    - runtime validation against `/home/piper/agilex/pour`

- Updated `scripts/foot_pedal_capture_toggle.py`.
  - Reason: user requested that the left foot pedal capture the current gripper position, current joint angles, and FK end pose into both `log` and `md` files before any reset behavior is added.
  - Evidence source:
    - source inspection of `scripts/foot_pedal_capture_toggle.py`
    - source inspection of `scripts/FOOT_PEDAL.md`
    - source inspection of `src/data_msgs/msg/Gripper.msg`
    - topic naming inspected under `src/` and `install/share/` for `/joint_states_single*`, `/joint_states_gripper*`, `/piper_FK*/urdf_end_pose_orient`, and `/sensor/gripper*`
  - Observed result:
    - left pedal `KEY_A` now records a runtime snapshot to `datasetDir/foot_pedal_state_snapshot.log` and `datasetDir/foot_pedal_state_snapshot.md`
    - right pedal `KEY_C` still toggles capture start/stop
    - middle pedal `KEY_B` remains unbound

- Updated `scripts/FOOT_PEDAL.md`.
  - Reason: document the new left-pedal snapshot behavior and the snapshot output file locations.
  - Evidence source:
    - source inspection of the updated foot pedal script

- Updated `analysis/piper_single_teleop_2026-04-10.md`.
  - Reason: record what this change confirms in code versus what still needs live runtime validation.
  - Evidence source:
    - source inspection of the updated foot pedal script and the expected runtime topic set

- `.gitignore` unchanged.
  - Reason: the new snapshot `log/md` files are written under the runtime dataset directory outside the repository, so no repository ignore rule was needed.

- Added `scripts/record_named_robot_pose.py`.
  - Reason: user clarified that they need a dedicated file for manually recording named restore/init candidates, separate from foot pedal runtime logs.
  - Evidence source:
    - live topic inspection with `rostopic list`, `rostopic info`, and `rosnode info`
    - source inspection of `install/share/pika_remote_piper/scripts/piper_FK.py`
  - Observed result:
    - the new script records one named pose entry into both `docs/robot_named_poses.json` and `docs/robot_named_poses.md`
    - the record keeps `joint_state`, `fk_pose`, `localization_pose`, and `gripper` separated so `/pika_pose_*` is not mistaken for actual arm FK pose

- Added `docs/robot_named_poses.json` and `docs/robot_named_poses.md`.
  - Reason: persist the current named pose candidate in both machine-readable and human-readable formats for later left-pedal init binding.
  - Evidence source:
    - `/usr/bin/python3 /home/piper/pika_ros/scripts/record_named_robot_pose.py --name current_init_pose_candidate`
  - Observed result:
    - current `current_init_pose_candidate` captured:
      - `localization_pose` on `/pika_pose_l` and `/pika_pose_r`
      - gripper state on `/gripper/gripper_l/data` and `/gripper/gripper_r/data`
      - `joint_state` unavailable on both arms in the current runtime
      - `fk_pose` unavailable because no live arm joint state was available to compute it

- Updated `analysis/piper_single_teleop_2026-04-10.md` again.
  - Reason: record that the current runtime can provide localization pose and gripper state, but not live arm joint state, which blocks creation of a true joint-space init pose from this run.
  - Evidence source:
    - `rostopic list`
    - `rostopic info /joint_states_single_l`
    - `rostopic info /joint_states_single_r`
    - `rostopic info /joint_states_gripper_l`
    - `rostopic echo -n 1 /gripper/gripper_l/data`
    - `rostopic echo -n 1 /gripper/gripper_r/data`
    - `rostopic echo -n 1 /pika_pose_l`
    - `rostopic echo -n 1 /pika_pose_r`
