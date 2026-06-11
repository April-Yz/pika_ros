# Teleop speed and acceleration change, 2026-05-11

## Scope

This change applies to the original data-collection teleop path:

```text
pipline.sh s4
  -> roslaunch pika_remote_piper teleop_rand_multi_piper.launch
  -> piper/launch/start_double_piper.launch
  -> piper_start_ms_node.py
```

It does not change the PI05 `s8` inference/deploy controller.

## Changes

- Changed active Piper joint/pose motion speed commands from `50` to `20` in `piper_start_ms_node.py`.
- Added startup-only joint max acceleration configuration in `mode == 1`:

```python
for motor_num in range(1, 7):
    self.piper.JointMaxAccConfig(motor_num, 100)
```

## Units

- `MotionCtrl_2(..., 20, ...)` uses Piper's motion speed rate field. This is the old `50` setting reduced to `20`.
- `JointMaxAccConfig(i, 100)` uses SDK units of `0.01 rad/s^2`, so `100` means `1.0 rad/s^2`.
- The SDK demo's `500` corresponds to `5.0 rad/s^2`.

## Notes

`JointMaxAccConfig` writes the motor acceleration limit through the Piper joint config command. The SDK demo notes this is written to driver flash and should not be sent at high frequency. For that reason, this repository change sends it once during controller startup, after `ConnectPort()` and before subscribing to teleop commands.

After changing the source, run:

```bash
cd ~/pika_ros
catkin_make install
source ~/pika_ros/install/setup.zsh
```

Then start the original teleop s4:

```bash
conda activate pika
source ~/pika_ros/install/setup.zsh
roslaunch pika_remote_piper teleop_rand_multi_piper.launch
```
