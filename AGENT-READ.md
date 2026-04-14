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
4. Review whether any newly created runtime files, caches, recordings, archives, or generated outputs should be ignored.
   - If they are not suitable for version control, add a precise rule to `.gitignore` before committing.
5. Make a Git commit for the change set after the logs and analysis are updated.
   - The commit message should match the actual content of the change.
   - Do not leave code edits uncommitted unless the user explicitly wants a dirty working tree.

Workflow rule for every future modification:

- change code or docs
- update `logs/change_log.md`
- update the latest relevant file under `analysis/`
- update `.gitignore` if new non-source artifacts appear
- commit the change set to Git

Repository focus for routine tracking:

- prefer tracking `src/`, `scripts/`, `docs/`, `analysis/`, `logs/`, and root config files
- avoid tracking generated ROS workspace outputs, caches, bag files, backup files, and bulky third-party drops unless there is a specific reason

Current debugging focus:

- `pika_remote_piper` single-arm teleop with `start_sensor_gripper.bash`
- verify `/pika_pose`, `/teleop_trigger`, `/piper_IK/ctrl_end_pose`, `/joint_states_gripper`
- keep shell-specific setup usage explicit:
  - `zsh` -> `source ~/pika_ros/install/setup.zsh`
  - `bash` -> `source ~/pika_ros/install/setup.bash`

Do not overwrite user changes in existing scripts unless the new behavior is verified and logged.
