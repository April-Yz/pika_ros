# Head D435 Capture Issue Log

Date: 2026-04-20

## Sessions Checked

- `tmux s7`
- `tmux s8`

## Findings

### `s7`

- Error pattern:
  `Compressed Depth Image Transport - Compression requires single-channel 32bit-floating point or 16bit raw depth images (input format is: rgb8).`
- Followed by:
  `cv_bridge exception: '[16UC1] is not a color format. but [bgr8] is. The conversion does not make sense'`

Conclusion:

- This is a code/topic usage error, not a hardware failure.
- A color image stream with encoding `rgb8` was being treated as a depth image somewhere in the capture path.
- At the same time, a depth image stream with encoding `16UC1` was also being treated as a color image.
- That means the RGB/depth roles were effectively mixed or handed to code that expected the opposite type.

Action taken:

- Reworked `record_head_d435_rgbd_with_pedal.py` so it no longer depends on `cv_bridge`.
- Added explicit ROS `Image` parsing by encoding:
  - `rgb8` -> BGR numpy image for RGB saving
  - `16UC1` / `32FC1` -> depth arrays
- This avoids the color/depth conversion path that produced the observed `cv_bridge` and depth transport errors in the custom recorder.

### `s8`

- Error pattern:
  `libcv_bridge.so: cannot open shared object file: No such file or directory`

Conclusion:

- This was primarily an environment/startup error, not a sensor logic bug.
- The recorder was started through `sudo -E`, and the root process did not have a usable ROS runtime library path for `libcv_bridge.so`.
- Because `cv_bridge` loads its shared library dynamically at runtime, the import succeeded but frame conversion failed once recording started.

Action taken:

- Removed `cv_bridge` usage from `record_head_d435_rgbd_with_pedal.py`.
- Added a dedicated launcher `start_head_d435_rgbd_pedal.sh`.
- The launcher now:
  - starts RealSense with color + aligned depth
  - waits for topics to appear
  - runs the pedal recorder with the required environment in one command

## Data Path

Previous run observed in `s8`:

- `/home/piper/agilex/pour_head/episode0`

New default path after update:

- `/home/piper/agilex/human/<task_name>/episodeN`

## Notes

- The previous `episode0` under `/home/piper/agilex/pour_head` was created before the dataset root default was changed.
- The updated pedal recorder now defaults to `/home/piper/agilex/human`.

## Additional Incident: 2026-04-20 20:28

Observed in `s7`:

- `Hardware Notification: Depth stream start failure`
- `Asic Temperature value is not valid!`
- repeated `control_transfer returned error`

Observed in `s8`:

- recorder started normally
- pedal toggle start/stop worked
- `episode0` created under `/home/piper/agilex/human/pnp_star_pear/episode0`
- `saved_frames=0`

Directory contents confirm only metadata was written:

- `camera/color/headD435_camera_info.json`
- `head_d435_rgbd_meta.json`

Conclusion:

- This incident is not a dataset path bug.
- This incident is not a pedal control bug.
- The dominant failure is on the D435 depth stream side. The recorder waits for synchronized RGB+depth pairs, and because the depth stream failed to start reliably, no synchronized frames were available to save.

Likely causes:

- unstable USB link / bandwidth
- camera firmware or hardware state
- camera overheating / sensor state issue hinted by invalid ASIC temperature messages
- camera node started in a bad state and needs a full restart or replug
