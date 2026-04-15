# Pika Device Binding Verification

## Purpose

This note is for verifying whether `setup_device.py` generated the correct udev binding and whether the current USB insertion matches the previously bound ports.

The binding in this repo is **port-based**, not purely device-ID-based:

- `sensor` uses `/dev/ttyUSB50`, `/dev/ttyUSB51`, `/dev/video50`, `/dev/video51`
- `gripper` uses `/dev/ttyUSB60`, `/dev/ttyUSB61`, `/dev/video60`, `/dev/video61`

After binding, the device must be plugged back into the same physical USB port.

## Clean Environment

Run this first:

```bash
conda deactivate
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH
unset PYTHONHOME
unset PYTHONPATH
cd ~/pika_ros/scripts
```

## Step 1: Verify Fixed Aliases Exist

```bash
ls -l /dev/ttyUSB50 /dev/ttyUSB51 /dev/ttyUSB60 /dev/ttyUSB61 \
      /dev/video50 /dev/video51 /dev/video60 /dev/video61
```

How to read it:

- The alias on the left is what matters.
- The real target on the right such as `ttyUSB2` or `video12` may change.
- If an alias is missing, that device is not currently bound on the expected port.

## Step 2: Verify USB Path Matches the Binding

```bash
udevadm info /dev/ttyUSB50 | grep DEVPATH
udevadm info /dev/ttyUSB51 | grep DEVPATH
udevadm info /dev/ttyUSB60 | grep DEVPATH
udevadm info /dev/ttyUSB61 | grep DEVPATH
udevadm info /dev/video50  | grep DEVPATH
udevadm info /dev/video51  | grep DEVPATH
udevadm info /dev/video60  | grep DEVPATH
udevadm info /dev/video61  | grep DEVPATH
```

Expected path fragments on this machine:

- `ttyUSB50` -> `1-2.4:1.0`
- `ttyUSB51` -> `1-4.4:1.0`
- `ttyUSB60` -> `1-1.4:1.0`
- `ttyUSB61` -> `1-11.4:1.0`
- `video50` -> `2-2.2:1.0`
- `video51` -> `2-4.2:1.0`
- `video60` -> `2-1.2:1.0`
- `video61` -> `2-10.2:1.0`

If the alias exists but the path is different, the wrong port was used during binding or after reinsertion.

## Step 3: Verify RealSense Device Identity

List current D405 devices:

```bash
rs-enumerate-devices -s
```

Check the serial numbers written into the startup scripts:

```bash
sed -n '1,20p' ~/pika_ros/scripts/start_multi_sensor.bash
sed -n '1,20p' ~/pika_ros/scripts/start_multi_gripper.bash
```

Current configured values in this repo:

- `start_multi_sensor.bash`
  - left: `412622273408`
  - right: `315122271385`
- `start_multi_gripper.bash`
  - left: `315122271600`
  - right: `230322273372`

If `rs-enumerate-devices -s` does not show the expected serial numbers, the startup script and the connected devices do not match.

## Step 4: Quick V4L2 Probe For Bound Video Nodes

```bash
v4l2-ctl -d /dev/video50 --all
v4l2-ctl -d /dev/video51 --all
v4l2-ctl -d /dev/video60 --all
v4l2-ctl -d /dev/video61 --all
```

If a node opens successfully, the video side is at least visible to Linux.

List supported formats:

```bash
v4l2-ctl -d /dev/video50 --list-formats-ext
v4l2-ctl -d /dev/video51 --list-formats-ext
```

## Step 5: Runtime Validation Through ROS

Start the two pipelines:

```bash
cd ~/pika_ros/scripts && bash start_multi_sensor.bash sensor
cd ~/pika_ros/scripts && bash start_multi_gripper.bash gripper sensor
```

Then inspect topics from another terminal:

```bash
rostopic list | grep -E 'pika_pose|joint_states_gripper|joint_states_single_gripper'
rostopic hz /joint_states_gripper_l /joint_states_gripper_r /joint_states_single_gripper_l /joint_states_single_gripper_r
```

There is also a built-in low-frequency monitor:

```bash
/usr/bin/python3 ~/pika_ros/scripts/lowfreq_dual_piper_monitor.py gripper
```

How to use it:

- Move only the left device and confirm only the `LEFT` values change.
- Move only the right device and confirm only the `RIGHT` values change.
- If left and right are swapped, the binding order is wrong even if the pipeline still runs.

## Visualize Bound Video Ports

### Option A: `ffplay`

Preview one port:

```bash
ffplay -fflags nobuffer -f v4l2 -framerate 30 -video_size 640x480 /dev/video50
```

Open different ports in separate terminals:

```bash
ffplay -fflags nobuffer -f v4l2 -framerate 30 -video_size 640x480 /dev/video50
ffplay -fflags nobuffer -f v4l2 -framerate 30 -video_size 640x480 /dev/video51
ffplay -fflags nobuffer -f v4l2 -framerate 30 -video_size 640x480 /dev/video60
ffplay -fflags nobuffer -f v4l2 -framerate 30 -video_size 640x480 /dev/video61
```

### Option B: Python Preview Helper

This repo now includes:

```bash
/usr/bin/python3 ~/pika_ros/scripts/preview_fisheye_ports.py
```

Preview specific aliases:

```bash
/usr/bin/python3 ~/pika_ros/scripts/preview_fisheye_ports.py video50 video51
/usr/bin/python3 ~/pika_ros/scripts/preview_fisheye_ports.py /dev/video60 /dev/video61
```

Press `q` in any preview window to quit.

Note:

- A bound alias such as `/dev/video50` may land on a RealSense metadata node instead of a directly viewable capture node.
- The preview helper now auto-resolves that alias to a sibling capture node on the same USB interface.
- In the current machine state:
  - `/dev/video50` resolves to `/dev/video14`
  - `/dev/video51` resolves to `/dev/video5`
  - `/dev/video60` can be opened directly
  - `/dev/video61` can be opened directly

## Current Check Result On 2026-04-14

Observed in the current session:

- `sensor` serial aliases exist:
  - `/dev/ttyUSB50`
  - `/dev/ttyUSB51`
- `gripper` serial aliases exist:
  - `/dev/ttyUSB60`
  - `/dev/ttyUSB61`
- `sensor` video aliases exist:
  - `/dev/video50`
  - `/dev/video51`
- `gripper` video aliases are missing:
  - `/dev/video60`
  - `/dev/video61`

USB path check result:

- `/dev/ttyUSB50` matches `1-2.4:1.0`
- `/dev/ttyUSB51` matches `1-4.4:1.0`
- `/dev/ttyUSB60` matches `1-1.4:1.0`
- `/dev/ttyUSB61` matches `1-11.4:1.0`
- `/dev/video50` matches `2-2.2:1.0`
- `/dev/video51` matches `2-4.2:1.0`

RealSense check result:

- Present now:
  - `412622273408`
  - `315122271385`
- This matches the two serials currently written in `start_multi_sensor.bash`
- It does **not** match the two serials written in `start_multi_gripper.bash`, because those devices are not currently present

Interpretation:

- `sensor` binding is currently consistent.
- `gripper` serial binding is present, but the expected bound video aliases are not currently available.
- For a full `gripper` verification, reinsert the two gripper devices into the originally bound USB ports and repeat Step 1 to Step 5.
