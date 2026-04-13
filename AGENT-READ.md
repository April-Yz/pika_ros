## Agent Read

This repository currently has local modifications and generated workspace artifacts.
Before changing code, read the latest file under `analysis/` and append an entry to `logs/change_log.md`.

If you modify anything, you must do all of the following:

1. Record the exact changed files in `logs/change_log.md`.
2. Record the reason for the change, the relevant command or log path, and the observed result.
3. Update the latest analysis file in `analysis/` with:
   - what was confirmed,
   - what is still only a hypothesis,
   - what runtime evidence supports the conclusion.

Current debugging focus:

- `pika_remote_piper` single-arm teleop with `start_sensor_gripper.bash`
- verify `/pika_pose`, `/teleop_trigger`, `/piper_IK/ctrl_end_pose`, `/joint_states_gripper`
- keep shell-specific setup usage explicit:
  - `zsh` -> `source ~/pika_ros/install/setup.zsh`
  - `bash` -> `source ~/pika_ros/install/setup.bash`

Do not overwrite user changes in existing scripts unless the new behavior is verified and logged.
