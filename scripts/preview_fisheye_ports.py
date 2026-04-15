#!/usr/bin/env /usr/bin/python3

import argparse
import os
import re
import subprocess
import sys

import cv2


def parse_args():
    parser = argparse.ArgumentParser(
        description="Preview one or more bound video aliases such as /dev/video50."
    )
    parser.add_argument(
        "devices",
        nargs="*",
        default=["/dev/video50", "/dev/video51", "/dev/video60", "/dev/video61"],
        help="Video devices to preview. Defaults to all bound aliases.",
    )
    parser.add_argument("--width", type=int, default=640, help="Requested width.")
    parser.add_argument("--height", type=int, default=480, help="Requested height.")
    parser.add_argument("--fps", type=int, default=30, help="Requested frame rate.")
    return parser.parse_args()


def normalize_device(value):
    if value.startswith("/dev/"):
        return value
    if value.startswith("video"):
        return f"/dev/{value}"
    return value


def run_command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        return result.stdout
    except Exception:
        return ""


def get_v4l2_info(device):
    return run_command(["v4l2-ctl", "-d", device, "--all"])


def get_devpath(device):
    output = run_command(["udevadm", "info", device])
    match = re.search(r"DEVPATH=(.+)", output)
    if not match:
        return None
    return match.group(1).strip()


def is_metadata_only(device):
    info = get_v4l2_info(device)
    return "Format Metadata Capture:" in info and "Format Video Capture:" not in info


def sibling_capture_candidates(device):
    devpath = get_devpath(device)
    if not devpath:
        return []
    prefix = devpath.rsplit("/video4linux/", 1)[0] + "/video4linux/"
    candidates = []
    for entry in sorted(os.listdir("/dev")):
        if not entry.startswith("video"):
            continue
        sibling = f"/dev/{entry}"
        sibling_devpath = get_devpath(sibling)
        if not sibling_devpath or not sibling_devpath.startswith(prefix):
            continue
        if sibling == device:
            continue
        info = get_v4l2_info(sibling)
        if "Format Video Capture:" not in info:
            continue
        score = 0
        if "Pixel Format      : 'YUYV'" in info:
            score += 30
        if "Pixel Format      : 'UYVY'" in info:
            score += 25
        if "Pixel Format      : 'GREY'" in info:
            score += 20
        if "Pixel Format      : 'Z16 '" in info:
            score += 5
        candidates.append((score, sibling))
    candidates.sort(reverse=True)
    return [device for _, device in candidates]


def resolve_preview_device(device):
    if not os.path.exists(device):
        return device, f"[missing] {device}"
    if not is_metadata_only(device):
        return device, None
    candidates = sibling_capture_candidates(device)
    if not candidates:
        return device, f"[metadata-only] {device} has no capture sibling"
    return candidates[0], f"[resolved] {device} -> {candidates[0]}"


def open_capture(device, width, height, fps):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def main():
    args = parse_args()
    devices = [normalize_device(d) for d in args.devices]
    opened = []

    for requested in devices:
        device, message = resolve_preview_device(requested)
        if message:
            print(message)
        if not os.path.exists(device):
            continue
        cap = open_capture(device, args.width, args.height, args.fps)
        if cap is None:
            print(f"[open-failed] {requested} -> {device}")
            continue
        opened.append((device, cap))
        cv2.namedWindow(device, cv2.WINDOW_NORMAL)

    if not opened:
        print("No video device could be opened.")
        return 1

    print("Preview started. Press q in any window to quit.")

    while True:
        any_frame = False
        for device, cap in opened:
            ok, frame = cap.read()
            if not ok or frame is None:
                blank = 255 * (cv2.UMat(args.height, args.width, cv2.CV_8UC3).get())
                cv2.putText(
                    blank,
                    f"{device}: no frame",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(device, blank)
                continue
            any_frame = True
            cv2.putText(
                frame,
                device,
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(device, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if not any_frame:
            key = cv2.waitKey(100) & 0xFF
            if key == ord("q"):
                break

    for _, cap in opened:
        cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
