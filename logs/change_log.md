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
