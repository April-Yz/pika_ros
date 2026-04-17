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
