# analyze_episode_hz 空白 SVG 排查

日期：2026-04-17

## 现象

执行：

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour
```

生成的 `hz_summary.svg` 可能出现两类异常：

- 图里没有曲线，summary 全是 `NaN`
- 曲线被压在最左侧，像是堆在第一帧附近

## 定位

`pour` 数据集当前使用的是：

- `/home/piper/agilex/pour/capture_status_hz_buffered_10hz.log`

这个日志里的 topic 名带有 `/buffered_capture/` 前缀，例如：

- `/buffered_capture/gripper/camera_l/color/image_raw`
- `/buffered_capture/camera/color/image_raw`

但 `scripts/analyze_episode_hz.py` 只匹配旧名字：

- `/gripper/camera_l/color/image_raw`
- `/camera/color/image_raw`

结果是日志记录虽然匹配到了 episode 时间窗，但频率点在 `summarize()` 里被全部过滤掉，最后 SVG 只有坐标轴和 legend，没有任何曲线。

另外，横轴原来只按 `capture_timing.log` 的起止时间画。如果实际命中的状态点略早于 0 秒或略晚于结束时间，曲线会被压缩到最左边，视觉上像“堆在第一帧”。

## 修复

本次修改：

- 在 `scripts/analyze_episode_hz.py` 增加 topic 规范化逻辑
  - 自动把 `/buffered_capture/...` 还原成旧 topic 名再参与统计
- 横轴改成按实际命中的数据时间范围和 episode 时长共同决定
  - 保留 `0s` 基准
  - 同时避免少量越界点把曲线挤到最左侧
- 批量模式下只要存在成功或已跳过的 episode，就不因为单个历史坏样本直接返回非零退出码
  - 例如 `pour/episode24/capture_timing.log` 不完整时，仍然不影响其余 episode 的批量扫描

## 验证

执行：

```bash
/usr/bin/python3 ~/pika_ros/scripts/analyze_episode_hz.py --task-name pour 30 --overwrite
```

结果：

- `episode30` 输出不再是全 `NaN`
- 重新生成的 `/home/piper/agilex/pour/episode30/hz_summary.svg` 包含有效 polyline 曲线
