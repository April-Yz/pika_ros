#!/usr/bin/env python3
import argparse
import json
import math
import os
import threading
import time

import cv2
import numpy as np
import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import CameraInfo, Image


def quat_to_rot(qx, qy, qz, qw):
    n = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if n < 1e-12:
        return np.eye(3)
    qx, qy, qz, qw = qx / n, qy / n, qz / n, qw / n
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ], dtype=np.float64)


def rot_to_quat(R):
    tr = float(np.trace(R))
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * s
        qx = (R[2, 1] - R[1, 2]) / s
        qy = (R[0, 2] - R[2, 0]) / s
        qz = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s
    q = np.array([qx, qy, qz, qw], dtype=np.float64)
    return q / np.linalg.norm(q)


def make_T(R, t):
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = np.asarray(R, dtype=np.float64).reshape(3, 3)
    T[:3, 3] = np.asarray(t, dtype=np.float64).reshape(3)
    return T


def inv_T(T):
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = T[:3, :3].T
    out[:3, 3] = -out[:3, :3].dot(T[:3, 3])
    return out


def pose_msg_to_T(msg):
    p = msg.pose.position
    q = msg.pose.orientation
    return make_T(quat_to_rot(q.x, q.y, q.z, q.w), [p.x, p.y, p.z])


def rvec_tvec_to_T(rvec, tvec):
    R, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    return make_T(R, np.asarray(tvec, dtype=np.float64).reshape(3))


def rot_angle_deg(R):
    v = (float(np.trace(R)) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, v))))


def T_to_dict(T):
    qx, qy, qz, qw = rot_to_quat(T[:3, :3])
    return {
        "translation": {"x": float(T[0, 3]), "y": float(T[1, 3]), "z": float(T[2, 3])},
        "rotation_quaternion_xyzw": {"x": float(qx), "y": float(qy), "z": float(qz), "w": float(qw)},
        "matrix": T.tolist(),
    }


def image_msg_to_bgr(msg):
    dtype = np.uint16 if msg.encoding in ("16UC1", "mono16") else np.uint8
    arr = np.frombuffer(msg.data, dtype=dtype)
    if msg.encoding in ("rgb8", "bgr8"):
        img = arr.reshape(msg.height, msg.step // 3, 3)[:, :msg.width, :]
        if msg.encoding == "rgb8":
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img.copy()
    if msg.encoding in ("mono8", "8UC1"):
        img = arr.reshape(msg.height, msg.step)[:, :msg.width]
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    raise ValueError("Unsupported image encoding: {}".format(msg.encoding))


def load_matrix_from_handeye(path, key):
    with open(path) as f:
        data = json.load(f)
    return np.asarray(data[key]["matrix"], dtype=np.float64)


def average_transforms(Ts):
    if not Ts:
        raise ValueError("no transforms to average")
    quats = []
    for T in Ts:
        q = rot_to_quat(T[:3, :3])
        if quats and np.dot(q, quats[0]) < 0:
            q = -q
        quats.append(q)
    q = np.mean(np.stack(quats), axis=0)
    q = q / np.linalg.norm(q)
    R = quat_to_rot(q[0], q[1], q[2], q[3])
    t = np.mean(np.stack([T[:3, 3] for T in Ts]), axis=0)
    return make_T(R, t)


def estimate_left_base_T_right_base(args, left_gripper_T_camera, right_gripper_T_camera):
    left_samples = np.load(args.left_samples, allow_pickle=True)
    right_samples = np.load(args.right_samples, allow_pickle=True)
    left_boards = [
        left_samples["base_T_gripper"][i].dot(left_gripper_T_camera).dot(left_samples["camera_T_board"][i])
        for i in range(len(left_samples["base_T_gripper"]))
    ]
    right_boards = [
        right_samples["base_T_gripper"][i].dot(right_gripper_T_camera).dot(right_samples["camera_T_board"][i])
        for i in range(len(right_samples["base_T_gripper"]))
    ]
    left_base_T_board = average_transforms(left_boards)
    right_base_T_board = average_transforms(right_boards)
    return left_base_T_board.dot(inv_T(right_base_T_board))


class CameraState:
    def __init__(self, name, image_topic, info_topic, detector, board_corners, min_corners):
        self.name = name
        self.image_topic = image_topic
        self.info_topic = info_topic
        self.detector = detector
        self.board_corners = board_corners
        self.min_corners = min_corners
        self.lock = threading.Lock()
        self.image = None
        self.image_stamp = None
        self.K = None
        self.D = None
        self.last_board_T = None
        self.last_corners = 0
        self.last_vis = None
        self.last_status = "waiting"
        rospy.Subscriber(image_topic, Image, self.image_cb, queue_size=1)
        rospy.Subscriber(info_topic, CameraInfo, self.info_cb, queue_size=1)

    def image_cb(self, msg):
        try:
            img = image_msg_to_bgr(msg)
        except Exception as exc:
            rospy.logwarn_throttle(2.0, "%s image parse failed: %s", self.name, exc)
            return
        with self.lock:
            self.image = img
            self.image_stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.Time.now().to_sec()

    def info_cb(self, msg):
        with self.lock:
            self.K = np.asarray(msg.K, dtype=np.float64).reshape(3, 3)
            self.D = np.asarray(msg.D, dtype=np.float64).reshape(-1, 1)

    def update_detection(self):
        with self.lock:
            if self.image is None:
                self.last_status = "no image: {}".format(self.image_topic)
                self.last_board_T = None
                self.last_corners = 0
                self.last_vis = self.placeholder(self.last_status)
                return None, 0, self.last_vis
            if self.K is None:
                self.last_status = "no camera_info: {}".format(self.info_topic)
                self.last_board_T = None
                self.last_corners = 0
                self.last_vis = self.placeholder(self.last_status)
                return None, 0, self.last_vis
            img = self.image.copy()
            K = self.K.copy()
            D = self.D.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        charuco_corners, charuco_ids, marker_corners, marker_ids = self.detector.detectBoard(gray)
        vis = img.copy()
        if marker_ids is not None and len(marker_ids) > 0:
            cv2.aruco.drawDetectedMarkers(vis, marker_corners, marker_ids)
        if charuco_ids is None or len(charuco_ids) < self.min_corners:
            board_T = None
            corners = 0
            status = "no board"
        else:
            cv2.aruco.drawDetectedCornersCharuco(vis, charuco_corners, charuco_ids)
            image_points = np.asarray(charuco_corners, dtype=np.float32).reshape(-1, 2)
            object_points = self.board_corners[np.asarray(charuco_ids, dtype=np.int32).reshape(-1)]
            ok, rvec, tvec = cv2.solvePnP(object_points, image_points, K, D, flags=cv2.SOLVEPNP_ITERATIVE)
            board_T = rvec_tvec_to_T(rvec, tvec) if ok else None
            corners = len(image_points)
            if ok:
                cv2.drawFrameAxes(vis, K, D, rvec, tvec, 0.037)
                status = "ok"
            else:
                status = "solvePnP failed"
        with self.lock:
            self.last_board_T = board_T
            self.last_corners = corners
            self.last_vis = vis
            self.last_status = status
        return board_T, corners, vis

    def placeholder(self, status):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, self.name, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(img, status, (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 180, 255), 2)
        cv2.putText(img, self.image_topic, (20, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(img, self.info_topic, (20, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        return img


class HeadFromWristCalibrator:
    def __init__(self, args):
        self.args = args
        dictionary = cv2.aruco.getPredefinedDictionary(args.aruco_dict)
        self.board = cv2.aruco.CharucoBoard((args.squares_x, args.squares_y), args.square_length, args.marker_length, dictionary)
        self.detector = cv2.aruco.CharucoDetector(self.board)
        self.board_corners = np.asarray(self.board.getChessboardCorners(), dtype=np.float32)

        self.left_gripper_T_camera = load_matrix_from_handeye(args.left_handeye, "gripper_T_camera")
        self.right_gripper_T_camera = load_matrix_from_handeye(args.right_handeye, "gripper_T_camera")
        if args.left_base_T_right_base:
            with open(args.left_base_T_right_base) as f:
                self.left_base_T_right_base = np.asarray(json.load(f)["left_base_T_right_base"]["matrix"], dtype=np.float64)
        else:
            self.left_base_T_right_base = estimate_left_base_T_right_base(args, self.left_gripper_T_camera, self.right_gripper_T_camera)

        self.left_fk = None
        self.right_fk = None
        self.left_fk_stamp = None
        self.right_fk_stamp = None
        self.fk_lock = threading.Lock()
        rospy.Subscriber(args.left_fk_topic, PoseStamped, self.left_fk_cb, queue_size=1)
        rospy.Subscriber(args.right_fk_topic, PoseStamped, self.right_fk_cb, queue_size=1)

        self.left_cam = CameraState("left", args.left_image_topic, args.left_info_topic, self.detector, self.board_corners, args.min_corners)
        self.right_cam = CameraState("right", args.right_image_topic, args.right_info_topic, self.detector, self.board_corners, args.min_corners)
        self.head_cam = CameraState("head", args.head_image_topic, args.head_info_topic, self.detector, self.board_corners, args.min_corners)
        self.samples = []

    def left_fk_cb(self, msg):
        with self.fk_lock:
            self.left_fk = pose_msg_to_T(msg)
            self.left_fk_stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.Time.now().to_sec()

    def right_fk_cb(self, msg):
        with self.fk_lock:
            self.right_fk = pose_msg_to_T(msg)
            self.right_fk_stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.Time.now().to_sec()

    def save_sample(self):
        left_cTboard, left_corners, _ = self.left_cam.update_detection()
        right_cTboard, right_corners, _ = self.right_cam.update_detection()
        head_cTboard, head_corners, _ = self.head_cam.update_detection()
        with self.fk_lock:
            left_fk = None if self.left_fk is None else self.left_fk.copy()
            right_fk = None if self.right_fk is None else self.right_fk.copy()

        if head_cTboard is None:
            return False, "head cam has no valid board detection"

        left_base_T_boards = []
        sources = []
        if left_cTboard is not None and left_fk is not None:
            left_base_T_boards.append(left_fk.dot(self.left_gripper_T_camera).dot(left_cTboard))
            sources.append("left")
        if right_cTboard is not None and right_fk is not None:
            right_base_T_board = right_fk.dot(self.right_gripper_T_camera).dot(right_cTboard)
            left_base_T_boards.append(self.left_base_T_right_base.dot(right_base_T_board))
            sources.append("right")
        if not left_base_T_boards:
            return False, "no wrist camera has a valid board detection"

        left_base_T_board = average_transforms(left_base_T_boards)
        left_base_T_head = left_base_T_board.dot(inv_T(head_cTboard))
        self.samples.append({
            "stamp": time.time(),
            "sources": sources,
            "left_base_T_board": left_base_T_board,
            "head_camera_T_board": head_cTboard,
            "left_base_T_head": left_base_T_head,
            "corners": {"left": left_corners, "right": right_corners, "head": head_corners},
        })
        return True, "sample {} saved, sources={}, corners={}".format(len(self.samples), sources, self.samples[-1]["corners"])

    def solve_and_save(self):
        if len(self.samples) < self.args.min_samples:
            raise RuntimeError("need at least {} samples, got {}".format(self.args.min_samples, len(self.samples)))
        left_base_T_head = average_transforms([s["left_base_T_head"] for s in self.samples])
        trans = []
        rots = []
        for s in self.samples:
            delta = inv_T(left_base_T_head).dot(s["left_base_T_head"])
            trans.append(float(np.linalg.norm(delta[:3, 3])))
            rots.append(rot_angle_deg(delta[:3, :3]))
        result = {
            "name": self.args.name,
            "mode": "head_from_wrist_moving_board",
            "sample_count": len(self.samples),
            "left_base_T_head_camera": T_to_dict(left_base_T_head),
            "left_base_T_right_base_used": T_to_dict(self.left_base_T_right_base),
            "residuals": {
                "translation_mean_m": float(np.mean(trans)),
                "translation_max_m": float(np.max(trans)),
                "rotation_mean_deg": float(np.mean(rots)),
                "rotation_max_deg": float(np.max(rots)),
            },
            "topics": {
                "left_image": self.args.left_image_topic,
                "right_image": self.args.right_image_topic,
                "head_image": self.args.head_image_topic,
                "left_fk": self.args.left_fk_topic,
                "right_fk": self.args.right_fk_topic,
            },
        }
        os.makedirs(self.args.output_dir, exist_ok=True)
        out_json = os.path.join(self.args.output_dir, "{}_head_from_wrist.json".format(self.args.name))
        with open(out_json, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        out_npz = os.path.join(self.args.output_dir, "samples_{}_head_from_wrist.npz".format(self.args.name))
        np.savez(
            out_npz,
            left_base_T_board=np.stack([s["left_base_T_board"] for s in self.samples]),
            head_camera_T_board=np.stack([s["head_camera_T_board"] for s in self.samples]),
            left_base_T_head=np.stack([s["left_base_T_head"] for s in self.samples]),
            meta=json.dumps(result, indent=2),
        )
        return out_json, result

    def run(self):
        print("Keys: s=save sample, q=solve and quit, Esc=quit")
        rate = rospy.Rate(15)
        while not rospy.is_shutdown():
            views = []
            for cam in (self.left_cam, self.right_cam, self.head_cam):
                _, corners, vis = cam.update_detection()
                cv2.putText(vis, "{} corners={} samples={} {}".format(cam.name, corners, len(self.samples), cam.last_status),
                            (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0) if corners else (0, 0, 255), 2)
                views.append(vis)
            if views:
                h = min(v.shape[0] for v in views)
                resized = [cv2.resize(v, (int(v.shape[1] * h / v.shape[0]), h)) for v in views]
                cv2.imshow("head_from_wrist_boards left/right/head", np.hstack(resized))
                key = cv2.waitKey(1) & 0xFF
                if key == ord("s"):
                    ok, msg = self.save_sample()
                    print(("[OK] " if ok else "[SKIP] ") + msg)
                elif key == ord("q"):
                    out, result = self.solve_and_save()
                    print("Saved result:", out)
                    print(json.dumps(result["residuals"], indent=2))
                    return
                elif key == 27:
                    print("Quit without solving")
                    return
            rate.sleep()


def parse_args():
    parser = argparse.ArgumentParser(description="Calibrate fixed head camera from moving Charuco board observed by calibrated wrist cameras.")
    parser.add_argument("--name", default="head_d435")
    parser.add_argument("--output-dir", default=os.path.expanduser("~/pika_ros/calibration/handeye"))
    parser.add_argument("--left-handeye", default=os.path.expanduser("~/pika_ros/calibration/handeye/left_wrist_eye_in_hand.json"))
    parser.add_argument("--right-handeye", default=os.path.expanduser("~/pika_ros/calibration/handeye/right_wrist_eye_in_hand.json"))
    parser.add_argument("--left-samples", default=os.path.expanduser("~/pika_ros/calibration/handeye/samples_left_wrist.npz"))
    parser.add_argument("--right-samples", default=os.path.expanduser("~/pika_ros/calibration/handeye/samples_right_wrist.npz"))
    parser.add_argument("--left-base-T-right-base", default="")
    parser.add_argument("--left-image-topic", default="/gripper/camera_l/color/image_raw")
    parser.add_argument("--left-info-topic", default="/gripper/camera_l/color/camera_info")
    parser.add_argument("--right-image-topic", default="/gripper/camera_r/color/image_raw")
    parser.add_argument("--right-info-topic", default="/gripper/camera_r/color/camera_info")
    parser.add_argument("--head-image-topic", default="/camera/color/image_raw")
    parser.add_argument("--head-info-topic", default="/camera/color/camera_info")
    parser.add_argument("--left-fk-topic", default="/piper_FK_l/urdf_end_pose_orient")
    parser.add_argument("--right-fk-topic", default="/piper_FK_r/urdf_end_pose_orient")
    parser.add_argument("--squares-x", type=int, default=7)
    parser.add_argument("--squares-y", type=int, default=5)
    parser.add_argument("--square-length", type=float, default=0.037)
    parser.add_argument("--marker-length", type=float, default=0.027)
    parser.add_argument("--aruco-dict", type=int, default=cv2.aruco.DICT_5X5_100)
    parser.add_argument("--min-corners", type=int, default=8)
    parser.add_argument("--min-samples", type=int, default=15)
    return parser.parse_args()


def main():
    args = parse_args()
    rospy.init_node("pika_calibrate_head_from_wrist_boards", anonymous=True)
    calibrator = HeadFromWristCalibrator(args)
    calibrator.run()


if __name__ == "__main__":
    main()
