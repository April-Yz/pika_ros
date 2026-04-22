# PIKA Try2 标定外参说明

本文档说明当前 `try2` 版本的左右腕相机、左右机械臂 base、Head D435 之间的外参关系和使用方式。

## 结论

Head D435 标定已经完成。当前 `try2` 结果：

```text
sample_count: 27
translation_mean_m: 0.008774
translation_max_m:  0.014875
rotation_mean_deg:  0.816
rotation_max_deg:   1.694
```

这个结果是可接受的。它表示 D435 的 color optical frame 已经标定到 `left_base` 坐标系下。

## 主要文件

推荐使用的严格一致 try2 总包：

```text
/home/piper/pika_ros/calibration/handeye/calibration_bundle_try2.json
```

用于对比的 mixed legacy 总包：

```text
/home/piper/pika_ros/calibration/handeye/calibration_bundle_legacy_wrist_try2_head.json
```

注意：`legacy_wrist_try2_head` 不是严格一致的 legacy 版本。它使用旧左右腕和旧左右 base 关系，但 Head D435 仍来自 `head_d435_try2`。如果需要严格的非 try2 版本，应使用旧左右腕参数重新运行一次 Head D435 标定。

## Try2 源文件

```text
left_wrist_try2_eye_in_hand.json
right_wrist_try2_eye_in_hand.json
left_base_T_right_base_try2.json
head_d435_try2_head_from_wrist.json
```

## 坐标系定义

```text
left_base
  左臂 FK base 坐标系

right_base
  右臂 FK base 坐标系

left_gripper
  /piper_FK_l/urdf_end_pose_orient 发布的左臂末端/TCP 坐标系

right_gripper
  /piper_FK_r/urdf_end_pose_orient 发布的右臂末端/TCP 坐标系

left_wrist_camera
  左腕部相机 color optical frame

right_wrist_camera
  右腕部相机 color optical frame

head_camera
  Head D435 color optical frame
```

RealSense optical frame 通常为：

```text
x: 图像右
y: 图像下
z: 相机前方
```

## 关键变换

所有矩阵命名都遵循：

```text
A_T_B
```

含义是把 `B` 坐标系下的点转换到 `A` 坐标系：

```text
P_A = A_T_B * P_B
```

### 左腕相机

```text
left_gripper_T_left_wrist_camera
```

使用方式：

```text
P_left_base = T_left_base_left_gripper * left_gripper_T_left_wrist_camera * P_left_wrist_camera
```

其中 `T_left_base_left_gripper` 来自：

```text
/piper_FK_l/urdf_end_pose_orient
```

### 右腕相机

```text
right_gripper_T_right_wrist_camera
```

转换到右臂 base：

```text
P_right_base = T_right_base_right_gripper * right_gripper_T_right_wrist_camera * P_right_wrist_camera
```

转换到左臂 base：

```text
P_left_base = left_base_T_right_base * T_right_base_right_gripper * right_gripper_T_right_wrist_camera * P_right_wrist_camera
```

### 左右 Base

```text
left_base_T_right_base
```

含义：

```text
P_left_base = left_base_T_right_base * P_right_base
```

反向变换也已经写入 bundle：

```text
right_base_T_left_base
```

### Head D435

```text
left_base_T_head_camera
```

含义：

```text
P_left_base = left_base_T_head_camera * P_head_camera
```

如果需要转换到右臂 base，bundle 中已经提供：

```text
right_base_T_head_camera
```

使用方式：

```text
P_right_base = right_base_T_head_camera * P_head_camera
```

## Try2 质量指标

左腕 try2：

```text
sample_count: 16
translation_mean_m: 0.006630
translation_max_m:  0.011292
rotation_mean_deg:  0.917
rotation_max_deg:   3.339
```

右腕 try2：

```text
sample_count: 18
translation_mean_m: 0.009378
translation_max_m:  0.013855
rotation_mean_deg:  1.094
rotation_max_deg:   1.775
```

左右 base try2 的固定板稳定性：

```text
left_board_spread.translation_mean_m:  0.006036
right_board_spread.translation_mean_m: 0.005294
```

Head D435 try2：

```text
sample_count: 27
translation_mean_m: 0.008774
translation_max_m:  0.014875
rotation_mean_deg:  0.816
rotation_max_deg:   1.694
```

## 重新导出总包

try2 总包：

```bash
/usr/bin/python3 ~/pika_ros/scripts/export_calibration_bundle.py \
  --name try2_full_calibration \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_try2_eye_in_hand.json \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_try2_eye_in_hand.json \
  --base-transform ~/pika_ros/calibration/handeye/left_base_T_right_base_try2.json \
  --head-handeye ~/pika_ros/calibration/handeye/head_d435_try2_head_from_wrist.json \
  --output ~/pika_ros/calibration/handeye/calibration_bundle_try2.json \
  --note 'Consistent try2 bundle: left/right wrist try2 hand-eye, try2 left_base_T_right_base, and head_d435_try2.'
```

mixed legacy 对比总包：

```bash
/usr/bin/python3 ~/pika_ros/scripts/export_calibration_bundle.py \
  --name legacy_wrist_with_try2_head_calibration \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json \
  --base-transform ~/pika_ros/calibration/handeye/left_base_T_right_base.json \
  --head-handeye ~/pika_ros/calibration/handeye/head_d435_try2_head_from_wrist.json \
  --output ~/pika_ros/calibration/handeye/calibration_bundle_legacy_wrist_try2_head.json \
  --note 'Mixed bundle: legacy left/right wrist and legacy left_base_T_right_base, but head camera transform comes from head_d435_try2. Use only for comparison; rerun head calibration with legacy inputs for a strictly consistent legacy bundle.'
```

## 严格非 Try2 Head 版本

如果需要严格的非 try2 head cam 标定，必须重新运行 Head D435 标定，并传入旧左右腕和旧左右 base：

```bash
/usr/bin/python3 ~/pika_ros/scripts/pika_calibrate_head_from_wrist_boards.py \
  --name head_d435_legacy \
  --left-handeye ~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json \
  --left-samples ~/pika_ros/calibration/handeye/samples_left_wrist.npz \
  --right-handeye ~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json \
  --right-samples ~/pika_ros/calibration/handeye/samples_right_wrist.npz \
  --left-base-T-right-base ~/pika_ros/calibration/handeye/left_base_T_right_base.json \
  --head-image-topic /camera/color/image_raw \
  --head-info-topic /camera/color/camera_info
```

运行完成后，再用 `export_calibration_bundle.py` 把 `head_d435_legacy_head_from_wrist.json` 导出成严格 legacy bundle。
