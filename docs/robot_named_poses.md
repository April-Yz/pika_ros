# Robot Named Poses

This file records manually captured robot pose candidates for later binding to reset/init actions.

## current_init_pose_candidate

- recorded_at: `2026-04-17T20:20:02.081997`
- note: `joint_state is the preferred source for reset/init binding; localization_pose is recorded separately and must not be treated as arm FK pose.`

### Arm `l`
- joint state: unavailable
- FK pose: unavailable
- localization topic: `/pika_pose_l`
- localization pose: `x=1.230833, y=-0.266831, z=-0.502442, qx=0.007119, qy=0.267932, qz=-0.801658, qw=0.534327`
- gripper topic: `/gripper/gripper_l/data`
- gripper: `angle=1.663400, distance=0.096391, effort=58.000000, velocity=0.000000, error=False, status=0x40`

### Arm `r`
- joint state: unavailable
- FK pose: unavailable
- localization topic: `/pika_pose_r`
- localization pose: `x=-0.076603, y=-0.138960, z=-0.174994, qx=-0.356906, qy=-0.257696, qz=0.793819, qw=-0.419598`
- gripper topic: `/gripper/gripper_r/data`
- gripper: `angle=1.670000, distance=0.096707, effort=-134.000000, velocity=0.000000, error=True, status=0x40`

## my_init_pose

- recorded_at: `2026-04-17T20:25:45.775324`
- note: `joint_state is the preferred source for reset/init binding; localization_pose is recorded separately and must not be treated as arm FK pose.`

### Arm `l`
- joint state: unavailable
- FK pose: unavailable
- localization topic: `/pika_pose_l`
- localization pose: `x=0.559109, y=-0.338174, z=-0.252094, qx=-0.302832, qy=-0.243849, qz=0.885146, qw=-0.255630`
- gripper topic: `/gripper/gripper_l/data`
- gripper: `angle=1.663600, distance=0.096401, effort=48.000000, velocity=0.000000, error=False, status=0x40`

### Arm `r`
- joint topic: `/joint_states_single_r`
- joint positions: `joint0=-0.035603, joint1=0.077975, joint2=0.005059, joint3=-0.122562, joint4=0.089156, joint5=-0.747458, joint6=0.000000`
- FK pose: unavailable (`fk_dependency_missing:No module named 'forward_inverse_kinematics'`)
- localization topic: `/pika_pose_r`
- localization pose: `x=-0.068031, y=-0.085574, z=-0.174110, qx=-0.348802, qy=-0.268547, qz=0.780102, qw=-0.444590`
- gripper topic: `/gripper/gripper_r/data`
- gripper: `angle=1.661500, distance=0.096300, effort=97.000000, velocity=0.000000, error=False, status=0x40`

## my_init_pose

- recorded_at: `2026-04-17T20:52:01.098600`
- note: `joint_state is the preferred source for reset/init binding; localization_pose is recorded separately and must not be treated as arm FK pose.`

### Arm `l`
- joint topic: `/joint_states_single_l`
- joint positions: `joint0=-0.226371, joint1=0.215154, joint2=0.012734, joint3=0.052524, joint4=0.028852, joint5=0.034243, joint6=0.000000`
- FK pose: unavailable (`fk_dependency_missing:No module named 'forward_inverse_kinematics'`)
- localization topic: `/pika_pose_l`
- localization pose: `x=0.674929, y=-0.167837, z=-0.027101, qx=-0.238941, qy=-0.203308, qz=0.903764, qw=-0.291177`
- gripper topic: `/gripper/gripper_l/data`
- gripper: `angle=1.661800, distance=0.096314, effort=86.000000, velocity=0.000000, error=False, status=0x40`

### Arm `r`
- joint topic: `/joint_states_single_r`
- joint positions: `joint0=-0.048861, joint1=0.259270, joint2=0.012176, joint3=-0.400724, joint4=0.023253, joint5=-0.410893, joint6=0.000000`
- FK pose: unavailable (`fk_dependency_missing:No module named 'forward_inverse_kinematics'`)
- localization topic: `/pika_pose_r`
- localization pose: `x=0.013710, y=-0.029666, z=-0.130216, qx=0.315572, qy=0.267933, qz=-0.700075, qw=0.581826`
- gripper topic: `/gripper/gripper_r/data`
- gripper: `angle=1.661600, distance=0.096305, effort=90.000000, velocity=0.000000, error=False, status=0x40`

## my_init_pose

- recorded_at: `2026-04-17T20:52:56.250882`
- note: `joint_state is the preferred source for reset/init binding; localization_pose is recorded separately and must not be treated as arm FK pose.`

### Arm `l`
- joint topic: `/joint_states_single_l`
- joint positions: `joint0=-0.023166, joint1=0.312457, joint2=-0.011897, joint3=-0.078167, joint4=0.007169, joint5=0.375063, joint6=0.000000`
- FK pose: unavailable (`fk_dependency_missing:No module named 'forward_inverse_kinematics'`)
- localization topic: `/pika_pose_l`
- localization pose: `x=0.676928, y=-0.171951, z=-0.027067, qx=-0.236750, qy=-0.206595, qz=0.899203, qw=-0.304468`
- gripper topic: `/gripper/gripper_l/data`
- gripper: `angle=1.670000, distance=0.096707, effort=-71.000000, velocity=0.000000, error=True, status=0x40`

### Arm `r`
- joint topic: `/joint_states_single_r`
- joint positions: `joint0=-0.046453, joint1=0.269266, joint2=-0.112985, joint3=-0.032847, joint4=0.166084, joint5=-0.825014, joint6=0.000000`
- FK pose: unavailable (`fk_dependency_missing:No module named 'forward_inverse_kinematics'`)
- localization topic: `/pika_pose_r`
- localization pose: `x=0.014986, y=-0.030441, z=-0.131796, qx=0.312566, qy=0.269963, qz=-0.694690, qw=0.588922`
- gripper topic: `/gripper/gripper_r/data`
- gripper: `angle=1.668500, distance=0.096636, effort=-24.000000, velocity=0.000000, error=False, status=0x40`
