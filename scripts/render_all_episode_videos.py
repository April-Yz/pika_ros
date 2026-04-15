#!/usr/bin/env /usr/bin/python3

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render overview videos for every episode directory under a dataset root."
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(Path.home() / "agilex" / "data"),
        help="Dataset root containing episode directories.",
    )
    parser.add_argument(
        "--output-name",
        default="camera_overview.mp4",
        help="Output file name inside each episode directory.",
    )
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--tile-width", type=int, default=640)
    parser.add_argument("--tile-height", type=int, default=480)
    parser.add_argument("--max-gap", type=float, default=0.25)
    parser.add_argument("--include-depth", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--only", nargs="*", default=None)
    return parser.parse_args()


def episode_sort_key(path: Path):
    suffix = path.name[len("episode") :]
    return (0, int(suffix)) if suffix.isdigit() else (1, path.name)


def build_command(args, episode_dir: Path):
    script = Path(__file__).resolve().parent / "render_episode_camera_video.py"
    output = episode_dir / args.output_name
    cmd = [
        sys.executable,
        str(script),
        str(episode_dir),
        "--dataset-dir",
        args.dataset_dir,
        "--output",
        str(output),
        "--fps",
        str(args.fps),
        "--tile-width",
        str(args.tile_width),
        "--tile-height",
        str(args.tile_height),
        "--max-gap",
        str(args.max_gap),
    ]
    if args.include_depth:
        cmd.append("--include-depth")
    if args.only:
        cmd.append("--only")
        cmd.extend(args.only)
    return cmd, output


def main():
    args = parse_args()
    dataset_dir = Path(args.dataset_dir).expanduser()
    if not dataset_dir.is_dir():
        raise SystemExit(f"Dataset directory not found: {dataset_dir}")

    episodes = sorted(
        [path for path in dataset_dir.iterdir() if path.is_dir() and path.name.startswith("episode")],
        key=episode_sort_key,
    )
    if not episodes:
        raise SystemExit(f"No episode directories found under {dataset_dir}")

    succeeded = []
    skipped = []
    failed = []

    for episode_dir in episodes:
        cmd, output = build_command(args, episode_dir)
        if output.exists() and not args.overwrite:
            print(f"[skip] {episode_dir.name}: {output.name} already exists")
            skipped.append(episode_dir.name)
            continue

        print(f"[run]  {episode_dir.name}")
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode == 0:
            print(f"[ok]   {episode_dir.name}: {output}")
            succeeded.append(episode_dir.name)
            continue

        print(f"[fail] {episode_dir.name}")
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip())
        failed.append(episode_dir.name)

    print("\nSummary")
    print(f"  succeeded: {len(succeeded)}")
    print(f"  skipped:   {len(skipped)}")
    print(f"  failed:    {len(failed)}")
    if succeeded:
        print("  success list:", ", ".join(succeeded))
    if skipped:
        print("  skipped list:", ", ".join(skipped))
    if failed:
        print("  failed list:", ", ".join(failed))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
