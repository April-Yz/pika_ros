# Issue Log: 2026-04-16 Render Episode Camera Video Multi-ID Support

## 问题

原脚本 `scripts/render_episode_camera_video.py` 只能接收单个 episode 参数，导致下面这种调用不可用：

```bash
/usr/bin/python3 ~/pika_ros/scripts/render_episode_camera_video.py 35 36 37 38 39 40 41 42 43
```

同时，脚本没有“已有输出则跳过”的保护，批量场景下容易重复合成已有视频。

## 调整后的行为

- `episodes` 参数改为可选列表，支持一次传入多个 episode id 或路径
- 不传 `episodes` 时，自动渲染 `--dataset-dir` 下所有 `episode*` 目录
- 默认情况下，如果目标 `camera_overview.mp4` 已存在，则跳过
- 需要强制重做时，使用 `--overwrite`
- `--output` 只允许在单个 episode 模式下使用，避免多个 episode 共用一个输出路径

## 对用户问题的直接回答

- 现在可以支持多个 id
- 不传 id 时，默认会遍历全部 episode
- 已有的 `camera_overview.mp4` 默认不会再合成一次，除非加 `--overwrite`

