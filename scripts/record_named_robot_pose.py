#!/usr/bin/env /usr/bin/python3

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _bootstrap_ros_python() -> None:
    script_dir = Path(__file__).resolve().parent
    workspace_dir = script_dir.parent
    candidates = [
        "/opt/ros/noetic/lib/python3/dist-packages",
        str(workspace_dir / "install" / "lib" / "python3" / "dist-packages"),
        str(workspace_dir / "devel" / "lib" / "python3" / "dist-packages"),
        str(workspace_dir / "install" / "share" / "pika_remote_piper" / "scripts"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.append(candidate)


try:
    import rospy
    from data_msgs.msg import Gripper
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import JointState
except ModuleNotFoundError:
    _bootstrap_ros_python()
    import rospy
    from data_msgs.msg import Gripper
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import JointState


def try_compute_fk_pose(joint_positions: Sequence[float]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if len(joint_positions) < 6:
        return None, "joint_state_has_fewer_than_6_positions"
    try:
        from forward_inverse_kinematics import Arm_FK  # type: ignore
    except ModuleNotFoundError as exc:
        return None, f"fk_dependency_missing:{exc}"

    class FKArgs:
        def __init__(self) -> None:
            self.lift = False
            self.gripper_xyzrpy = [0.19, 0.0, 0.0, 0.0, 0.0, 0.0]

    fk = Arm_FK(FKArgs())
    xyzrpy = fk.get_pose(joint_positions[:6])
    return {
        "position": {
            "x": float(xyzrpy[0]),
            "y": float(xyzrpy[1]),
            "z": float(xyzrpy[2]),
        },
        "rpy": {
            "roll": float(xyzrpy[3]),
            "pitch": float(xyzrpy[4]),
            "yaw": float(xyzrpy[5]),
        },
    }, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record the current robot state into dedicated JSON and Markdown files."
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Human-readable pose name. Default: init_pose_candidate_<timestamp>",
    )
    parser.add_argument(
        "--json-path",
        default=str(Path.home() / "pika_ros" / "docs" / "robot_named_poses.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--md-path",
        default=str(Path.home() / "pika_ros" / "docs" / "robot_named_poses.md"),
        help="Output Markdown path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Timeout in seconds for each topic read. Default: 2.0",
    )
    return parser.parse_args()


def wait_for_message(topic: str, msg_type: Any, timeout: float) -> Optional[Any]:
    try:
        return rospy.wait_for_message(topic, msg_type, timeout=timeout)
    except rospy.ROSException:
        return None


def topic_exists(topic: str, expected_type: str, published_topics: Dict[str, str]) -> bool:
    return published_topics.get(topic) == expected_type


def pose_to_dict(msg: PoseStamped) -> Dict[str, Any]:
    pose = msg.pose
    return {
        "frame_id": msg.header.frame_id,
        "stamp": {"secs": msg.header.stamp.secs, "nsecs": msg.header.stamp.nsecs},
        "position": {
            "x": pose.position.x,
            "y": pose.position.y,
            "z": pose.position.z,
        },
        "orientation": {
            "x": pose.orientation.x,
            "y": pose.orientation.y,
            "z": pose.orientation.z,
            "w": pose.orientation.w,
        },
    }


def joint_state_to_dict(msg: JointState) -> Dict[str, Any]:
    return {
        "stamp": {"secs": msg.header.stamp.secs, "nsecs": msg.header.stamp.nsecs},
        "name": list(msg.name),
        "position": list(msg.position),
        "velocity": list(msg.velocity),
        "effort": list(msg.effort),
    }


def gripper_to_dict(msg: Gripper) -> Dict[str, Any]:
    return {
        "stamp": {"secs": msg.header.stamp.secs, "nsecs": msg.header.stamp.nsecs},
        "angle": msg.angle,
        "distance": msg.distance,
        "effort": msg.effort,
        "velocity": msg.velocity,
        "enable": msg.enable,
        "error": msg.error,
        "status": msg.status,
        "voltage": msg.voltage,
        "driver_temp": msg.driver_temp,
        "motor_temp": msg.motor_temp,
        "bus_current": msg.bus_current,
    }


def capture_arm_state(
    arm: str,
    published_topics: Dict[str, str],
    timeout: float,
) -> Dict[str, Any]:
    suffix = f"_{arm}"
    joint_candidates: List[Tuple[str, str]] = [
        (f"/joint_states_single{suffix}", "sensor_msgs/JointState"),
        (f"/joint_states_gripper{suffix}", "sensor_msgs/JointState"),
        (f"/joint_states_single_gripper{suffix}", "sensor_msgs/JointState"),
        (f"/joint_states{suffix}", "sensor_msgs/JointState"),
    ]
    joint_result: Dict[str, Any] = {"topic": None, "data": None, "status": "unavailable"}
    for topic, expected_type in joint_candidates:
        if not topic_exists(topic, expected_type, published_topics):
            continue
        msg = wait_for_message(topic, JointState, timeout)
        if msg is None:
            continue
        joint_result = {
            "topic": topic,
            "data": joint_state_to_dict(msg),
            "status": "ok",
        }
        break

    fk_result: Dict[str, Any] = {"status": "unavailable", "data": None, "reason": None}
    if joint_result["data"] is not None:
        fk_pose, fk_reason = try_compute_fk_pose(joint_result["data"]["position"])
        if fk_pose is not None:
            fk_result = {"status": "computed_from_joint_state", "data": fk_pose, "reason": None}
        else:
            fk_result = {"status": "unavailable", "data": None, "reason": fk_reason}

    localization_topic = f"/pika_pose{suffix}"
    localization_result: Dict[str, Any] = {
        "topic": localization_topic,
        "status": "unavailable",
        "data": None,
    }
    if topic_exists(localization_topic, "geometry_msgs/PoseStamped", published_topics):
        msg = wait_for_message(localization_topic, PoseStamped, timeout)
        if msg is not None:
            localization_result = {
                "topic": localization_topic,
                "status": "ok",
                "data": pose_to_dict(msg),
            }

    gripper_topic = f"/gripper/gripper{suffix}/data"
    gripper_result: Dict[str, Any] = {
        "topic": gripper_topic,
        "status": "unavailable",
        "data": None,
    }
    if topic_exists(gripper_topic, "data_msgs/Gripper", published_topics):
        msg = wait_for_message(gripper_topic, Gripper, timeout)
        if msg is not None:
            gripper_result = {
                "topic": gripper_topic,
                "status": "ok",
                "data": gripper_to_dict(msg),
            }

    return {
        "arm": arm,
        "joint_state": joint_result,
        "fk_pose": fk_result,
        "localization_pose": localization_result,
        "gripper": gripper_result,
    }


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"poses": []}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")


def format_float(value: Optional[float]) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.6f}"


def arm_summary_lines(arm_data: Dict[str, Any]) -> List[str]:
    arm = arm_data["arm"]
    lines = [f"### Arm `{arm}`"]

    joint_state = arm_data["joint_state"]
    if joint_state["data"] is not None:
        names = joint_state["data"]["name"]
        positions = joint_state["data"]["position"]
        pairs = []
        for idx, position in enumerate(positions):
            name = names[idx] if idx < len(names) else f"joint{idx + 1}"
            pairs.append(f"{name}={position:.6f}")
        lines.append(f"- joint topic: `{joint_state['topic']}`")
        lines.append(f"- joint positions: `{', '.join(pairs)}`")
    else:
        lines.append("- joint state: unavailable")

    fk_pose = arm_data["fk_pose"]
    if fk_pose["data"] is not None:
        pos = fk_pose["data"]["position"]
        rpy = fk_pose["data"]["rpy"]
        lines.append(
            "- FK pose: "
            f"`x={pos['x']:.6f}, y={pos['y']:.6f}, z={pos['z']:.6f}, "
            f"roll={rpy['roll']:.6f}, pitch={rpy['pitch']:.6f}, yaw={rpy['yaw']:.6f}`"
        )
    else:
        reason = fk_pose.get("reason")
        if reason:
            lines.append(f"- FK pose: unavailable (`{reason}`)")
        else:
            lines.append("- FK pose: unavailable")

    localization_pose = arm_data["localization_pose"]
    if localization_pose["data"] is not None:
        pos = localization_pose["data"]["position"]
        ori = localization_pose["data"]["orientation"]
        lines.append(f"- localization topic: `{localization_pose['topic']}`")
        lines.append(
            "- localization pose: "
            f"`x={pos['x']:.6f}, y={pos['y']:.6f}, z={pos['z']:.6f}, "
            f"qx={ori['x']:.6f}, qy={ori['y']:.6f}, qz={ori['z']:.6f}, qw={ori['w']:.6f}`"
        )
    else:
        lines.append("- localization pose: unavailable")

    gripper = arm_data["gripper"]
    if gripper["data"] is not None:
        data = gripper["data"]
        lines.append(f"- gripper topic: `{gripper['topic']}`")
        lines.append(
            "- gripper: "
            f"`angle={data['angle']:.6f}, distance={data['distance']:.6f}, "
            f"effort={data['effort']:.6f}, velocity={data['velocity']:.6f}, "
            f"error={data['error']}, status={data['status']}`"
        )
    else:
        lines.append("- gripper: unavailable")

    lines.append("")
    return lines


def write_markdown(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Robot Named Poses",
        "",
        "This file records manually captured robot pose candidates for later binding to reset/init actions.",
        "",
    ]
    for pose in payload.get("poses", []):
        lines.append(f"## {pose['name']}")
        lines.append("")
        lines.append(f"- recorded_at: `{pose['recorded_at']}`")
        lines.append(f"- note: `{pose['note']}`")
        lines.append("")
        for arm_key in ("l", "r"):
            lines.extend(arm_summary_lines(pose["arms"][arm_key]))
    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    now = dt.datetime.now()
    pose_name = args.name or f"init_pose_candidate_{now.strftime('%Y%m%d_%H%M%S')}"
    json_path = Path(args.json_path).expanduser()
    md_path = Path(args.md_path).expanduser()

    rospy.init_node("record_named_robot_pose", anonymous=True)
    published_topics = dict(rospy.get_published_topics())

    record = {
        "name": pose_name,
        "recorded_at": now.isoformat(),
        "note": (
            "joint_state is the preferred source for reset/init binding; "
            "localization_pose is recorded separately and must not be treated as arm FK pose."
        ),
        "arms": {
            "l": capture_arm_state("l", published_topics, args.timeout),
            "r": capture_arm_state("r", published_topics, args.timeout),
        },
    }

    payload = load_json(json_path)
    payload.setdefault("poses", [])
    payload["poses"].append(record)
    write_json(json_path, payload)
    write_markdown(md_path, payload)

    print(f"Recorded pose: {pose_name}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    for arm in ("l", "r"):
        joint_status = record["arms"][arm]["joint_state"]["status"]
        fk_status = record["arms"][arm]["fk_pose"]["status"]
        localization_status = record["arms"][arm]["localization_pose"]["status"]
        gripper_status = record["arms"][arm]["gripper"]["status"]
        print(
            f"arm={arm} joint_state={joint_status} fk_pose={fk_status} "
            f"localization_pose={localization_status} gripper={gripper_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
