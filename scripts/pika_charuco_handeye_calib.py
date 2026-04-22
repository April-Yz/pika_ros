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
from scipy.optimize import least_squares


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


def T_to_rvec_tvec(T):
    rvec, _ = cv2.Rodrigues(T[:3, :3])
    return rvec.reshape(3), T[:3, 3].reshape(3)


def T_to_dict(T):
    qx, qy, qz, qw = rot_to_quat(T[:3, :3])
    return {
        "translation": {
            "x": float(T[0, 3]),
            "y": float(T[1, 3]),
            "z": float(T[2, 3]),
        },
        "rotation_quaternion_xyzw": {
            "x": float(qx),
            "y": float(qy),
            "z": float(qz),
            "w": float(qw),
        },
        "matrix": T.tolist(),
    }


def transform_delta(base_T_a, base_T_b):
    delta = inv_T(base_T_a).dot(base_T_b)
    rvec, _ = cv2.Rodrigues(delta[:3, :3])
    return float(np.linalg.norm(delta[:3, 3])), float(np.rad2deg(np.linalg.norm(rvec)))


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
    if msg.encoding in ("16UC1", "mono16"):
        img = arr.reshape(msg.height, msg.step // 2)[:, :msg.width]
        img8 = cv2.convertScaleAbs(img, alpha=255.0 / max(1.0, float(np.max(img))))
        return cv2.cvtColor(img8, cv2.COLOR_GRAY2BGR)
    raise ValueError("Unsupported image encoding: {}".format(msg.encoding))


class CharucoHandeyeCalibrator:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.latest_image = None
        self.latest_image_stamp = None
        self.latest_robot_T = None
        self.latest_robot_stamp = None
        self.K = None
        self.D = None
        self.samples = []
        self.last_detection = None

        dictionary = cv2.aruco.getPredefinedDictionary(args.aruco_dict)
        self.board = cv2.aruco.CharucoBoard(
            (args.squares_x, args.squares_y),
            args.square_length,
            args.marker_length,
            dictionary,
        )
        self.detector = cv2.aruco.CharucoDetector(self.board)
        self.object_corners = np.asarray(self.board.getChessboardCorners(), dtype=np.float32)

        rospy.Subscriber(args.image_topic, Image, self.image_cb, queue_size=1)
        rospy.Subscriber(args.camera_info_topic, CameraInfo, self.camera_info_cb, queue_size=1)
        rospy.Subscriber(args.robot_pose_topic, PoseStamped, self.robot_pose_cb, queue_size=1)
        if args.resume_samples:
            self.load_samples(args.resume_samples)

    def load_samples(self, path):
        data = np.load(path, allow_pickle=True)
        base_T_gripper = data["base_T_gripper"]
        camera_T_board = data["camera_T_board"]
        if len(base_T_gripper) != len(camera_T_board):
            raise RuntimeError("resume sample count mismatch in {}".format(path))
        for bTg, cTt in zip(base_T_gripper, camera_T_board):
            self.samples.append({
                "stamp": None,
                "image_stamp": None,
                "robot_stamp": None,
                "base_T_gripper": np.asarray(bTg, dtype=np.float64).copy(),
                "camera_T_board": np.asarray(cTt, dtype=np.float64).copy(),
            })
        print("Loaded {} previous samples from {}".format(len(self.samples), path))

    def image_cb(self, msg):
        try:
            img = image_msg_to_bgr(msg)
        except Exception as exc:
            rospy.logwarn_throttle(2.0, "image parse failed: %s", exc)
            return
        with self.lock:
            self.latest_image = img
            self.latest_image_stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.Time.now().to_sec()

    def camera_info_cb(self, msg):
        with self.lock:
            self.K = np.asarray(msg.K, dtype=np.float64).reshape(3, 3)
            self.D = np.asarray(msg.D, dtype=np.float64).reshape(-1, 1)

    def robot_pose_cb(self, msg):
        with self.lock:
            self.latest_robot_T = pose_msg_to_T(msg)
            self.latest_robot_stamp = msg.header.stamp.to_sec() if msg.header.stamp else rospy.Time.now().to_sec()

    def detect_board(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        charuco_corners, charuco_ids, marker_corners, marker_ids = self.detector.detectBoard(gray)
        vis = image.copy()
        if marker_ids is not None and len(marker_ids) > 0:
            cv2.aruco.drawDetectedMarkers(vis, marker_corners, marker_ids)
        if charuco_ids is None or len(charuco_ids) < self.args.min_corners:
            return None, vis, 0

        cv2.aruco.drawDetectedCornersCharuco(vis, charuco_corners, charuco_ids)
        image_points = np.asarray(charuco_corners, dtype=np.float32).reshape(-1, 2)
        object_points = self.object_corners[np.asarray(charuco_ids, dtype=np.int32).reshape(-1)]
        ok, rvec, tvec = cv2.solvePnP(
            object_points,
            image_points,
            self.K,
            self.D,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return None, vis, len(image_points)
        cv2.drawFrameAxes(vis, self.K, self.D, rvec, tvec, self.args.square_length)
        return rvec_tvec_to_T(rvec, tvec), vis, len(image_points)

    def add_sample(self):
        with self.lock:
            if self.latest_image is None or self.latest_robot_T is None or self.K is None:
                return False, "missing image, robot pose, or camera_info"
            if self.last_detection is None:
                return False, "no valid Charuco detection"
            age = abs((self.latest_image_stamp or 0.0) - (self.latest_robot_stamp or 0.0))
            if age > self.args.max_time_offset:
                return False, "image/FK timestamp offset {:.3f}s > {:.3f}s".format(age, self.args.max_time_offset)
            if self.samples:
                dt, dr = transform_delta(self.samples[-1]["base_T_gripper"], self.latest_robot_T)
                if dt < self.args.min_robot_translation_delta and dr < self.args.min_robot_rotation_delta:
                    return False, (
                        "robot FK changed too little since last sample "
                        "({:.4f}m, {:.2f}deg). Move the arm or check FK topic."
                    ).format(dt, dr)
            sample = {
                "stamp": time.time(),
                "image_stamp": self.latest_image_stamp,
                "robot_stamp": self.latest_robot_stamp,
                "base_T_gripper": self.latest_robot_T.copy(),
                "camera_T_board": self.last_detection.copy(),
            }
            self.samples.append(sample)
            return True, "sample {} saved, timestamp offset {:.3f}s".format(len(self.samples), age)

    def save_raw_samples(self):
        os.makedirs(self.args.output_dir, exist_ok=True)
        path = os.path.join(self.args.output_dir, "samples_{}.npz".format(self.args.name))
        np.savez(
            path,
            base_T_gripper=np.stack([s["base_T_gripper"] for s in self.samples]),
            camera_T_board=np.stack([s["camera_T_board"] for s in self.samples]),
            meta=json.dumps({
                "name": self.args.name,
                "mode": self.args.mode,
                "image_topic": self.args.image_topic,
                "camera_info_topic": self.args.camera_info_topic,
                "robot_pose_topic": self.args.robot_pose_topic,
                "squares_x": self.args.squares_x,
                "squares_y": self.args.squares_y,
                "square_length": self.args.square_length,
                "marker_length": self.args.marker_length,
                "aruco_dict": self.args.aruco_dict,
            }, indent=2),
        )
        return path

    def solve_eye_in_hand(self):
        R_gripper2base = []
        t_gripper2base = []
        R_target2cam = []
        t_target2cam = []
        for sample in self.samples:
            bTg = sample["base_T_gripper"]
            cTt = sample["camera_T_board"]
            R_gripper2base.append(bTg[:3, :3])
            t_gripper2base.append(bTg[:3, 3].reshape(3, 1))
            R_target2cam.append(cTt[:3, :3])
            t_target2cam.append(cTt[:3, 3].reshape(3, 1))
        R_cam2gripper, t_cam2gripper = cv2.calibrateHandEye(
            R_gripper2base,
            t_gripper2base,
            R_target2cam,
            t_target2cam,
            method=cv2.CALIB_HAND_EYE_TSAI,
        )
        return make_T(R_cam2gripper, t_cam2gripper)

    def solve_eye_to_hand(self):
        base_T_gripper = [s["base_T_gripper"] for s in self.samples]
        camera_T_board = [s["camera_T_board"] for s in self.samples]

        # X = base_T_camera, Y = gripper_T_board.
        first_X = base_T_gripper[0].dot(inv_T(camera_T_board[0]))
        first_Y = np.eye(4, dtype=np.float64)
        xr, xt = T_to_rvec_tvec(first_X)
        yr, yt = T_to_rvec_tvec(first_Y)
        x0 = np.concatenate([xr, xt, yr, yt])

        def params_to_transforms(params):
            XR, _ = cv2.Rodrigues(params[0:3].reshape(3, 1))
            YR, _ = cv2.Rodrigues(params[6:9].reshape(3, 1))
            X = make_T(XR, params[3:6])
            Y = make_T(YR, params[9:12])
            return X, Y

        def residual(params):
            X, Y = params_to_transforms(params)
            out = []
            for bTg, cTt in zip(base_T_gripper, camera_T_board):
                left = bTg.dot(Y)
                right = X.dot(cTt)
                delta = inv_T(left).dot(right)
                rvec, _ = cv2.Rodrigues(delta[:3, :3])
                out.extend((self.args.rotation_weight * rvec.reshape(3)).tolist())
                out.extend(delta[:3, 3].reshape(3).tolist())
            return np.asarray(out, dtype=np.float64)

        result = least_squares(residual, x0, max_nfev=2000, xtol=1e-12, ftol=1e-12, gtol=1e-12)
        X, Y = params_to_transforms(result.x)
        return X, Y, result

    def compute_residuals(self, eye_in_hand_T=None, eye_to_hand_X=None, eye_to_hand_Y=None):
        translations = []
        rotations = []
        if self.args.mode == "eye_in_hand":
            base_T_board_list = []
            for sample in self.samples:
                bTg = sample["base_T_gripper"]
                cTt = sample["camera_T_board"]
                base_T_board_list.append(bTg.dot(eye_in_hand_T).dot(cTt))
            ref = base_T_board_list[0]
            for T in base_T_board_list[1:]:
                delta = inv_T(ref).dot(T)
                rvec, _ = cv2.Rodrigues(delta[:3, :3])
                translations.append(float(np.linalg.norm(delta[:3, 3])))
                rotations.append(float(np.linalg.norm(rvec)))
        else:
            for sample in self.samples:
                left = sample["base_T_gripper"].dot(eye_to_hand_Y)
                right = eye_to_hand_X.dot(sample["camera_T_board"])
                delta = inv_T(left).dot(right)
                rvec, _ = cv2.Rodrigues(delta[:3, :3])
                translations.append(float(np.linalg.norm(delta[:3, 3])))
                rotations.append(float(np.linalg.norm(rvec)))
        return {
            "translation_mean_m": float(np.mean(translations)) if translations else 0.0,
            "translation_max_m": float(np.max(translations)) if translations else 0.0,
            "rotation_mean_deg": float(np.rad2deg(np.mean(rotations))) if rotations else 0.0,
            "rotation_max_deg": float(np.rad2deg(np.max(rotations))) if rotations else 0.0,
        }

    def solve_and_save(self):
        if len(self.samples) < self.args.min_samples:
            raise RuntimeError("need at least {} samples, got {}".format(self.args.min_samples, len(self.samples)))
        os.makedirs(self.args.output_dir, exist_ok=True)
        samples_path = self.save_raw_samples()
        result = {
            "name": self.args.name,
            "mode": self.args.mode,
            "sample_count": len(self.samples),
            "samples_npz": samples_path,
            "topics": {
                "image": self.args.image_topic,
                "camera_info": self.args.camera_info_topic,
                "robot_pose": self.args.robot_pose_topic,
            },
            "board": {
                "squares_x": self.args.squares_x,
                "squares_y": self.args.squares_y,
                "square_length_m": self.args.square_length,
                "marker_length_m": self.args.marker_length,
                "aruco_dict": self.args.aruco_dict,
            },
        }
        if self.args.mode == "eye_in_hand":
            gripper_T_camera = self.solve_eye_in_hand()
            result["gripper_T_camera"] = T_to_dict(gripper_T_camera)
            result["residuals"] = self.compute_residuals(eye_in_hand_T=gripper_T_camera)
        else:
            base_T_camera, gripper_T_board, opt_result = self.solve_eye_to_hand()
            result["base_T_camera"] = T_to_dict(base_T_camera)
            result["gripper_T_board"] = T_to_dict(gripper_T_board)
            result["optimizer"] = {
                "success": bool(opt_result.success),
                "cost": float(opt_result.cost),
                "message": str(opt_result.message),
            }
            result["residuals"] = self.compute_residuals(
                eye_to_hand_X=base_T_camera,
                eye_to_hand_Y=gripper_T_board,
            )

        output_path = os.path.join(self.args.output_dir, "{}_{}.json".format(self.args.name, self.args.mode))
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        return output_path, result

    def run(self):
        print("Waiting for image, camera_info, and FK pose...")
        print("Keys: s=save sample, q=solve and quit, Esc=quit without solving")
        rate = rospy.Rate(30)
        while not rospy.is_shutdown():
            with self.lock:
                img = None if self.latest_image is None else self.latest_image.copy()
                has_info = self.K is not None
                has_robot = self.latest_robot_T is not None

            if img is not None and has_info:
                board_T, vis, corners = self.detect_board(img)
                with self.lock:
                    self.last_detection = board_T
                status = "samples={} corners={} FK={} camera_info={}".format(
                    len(self.samples),
                    corners,
                    "yes" if has_robot else "no",
                    "yes" if has_info else "no",
                )
                color = (0, 220, 0) if board_T is not None and has_robot else (0, 0, 255)
                cv2.putText(vis, status, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                cv2.putText(vis, "s: sample  q: solve  esc: quit", (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                cv2.imshow("pika_charuco_handeye_calib", vis)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("s"):
                    ok, msg = self.add_sample()
                    print(("[OK] " if ok else "[SKIP] ") + msg)
                elif key == ord("q"):
                    output_path, result = self.solve_and_save()
                    print("Saved result:", output_path)
                    print(json.dumps(result["residuals"], indent=2))
                    return
                elif key == 27:
                    print("Quit without solving")
                    return
            rate.sleep()


def parse_args():
    parser = argparse.ArgumentParser(description="PIKA Charuco hand-eye calibration helper.")
    parser.add_argument("--mode", choices=["eye_in_hand", "eye_to_hand"], required=True)
    parser.add_argument("--name", required=True, help="Result name, e.g. right_wrist or head_d435_left_base.")
    parser.add_argument("--image-topic", required=True)
    parser.add_argument("--camera-info-topic", required=True)
    parser.add_argument("--robot-pose-topic", required=True, help="FK PoseStamped topic, e.g. /piper_FK_r/urdf_end_pose_orient.")
    parser.add_argument("--output-dir", default=os.path.expanduser("~/pika_ros/calibration/handeye"))
    parser.add_argument("--resume-samples", default="", help="Optional .npz file to append samples to before solving.")
    parser.add_argument("--squares-x", type=int, default=7)
    parser.add_argument("--squares-y", type=int, default=5)
    parser.add_argument("--square-length", type=float, default=0.037)
    parser.add_argument("--marker-length", type=float, default=0.027)
    parser.add_argument("--aruco-dict", type=int, default=cv2.aruco.DICT_5X5_100)
    parser.add_argument("--min-corners", type=int, default=8)
    parser.add_argument("--min-samples", type=int, default=15)
    parser.add_argument("--max-time-offset", type=float, default=0.25)
    parser.add_argument("--min-robot-translation-delta", type=float, default=0.005)
    parser.add_argument("--min-robot-rotation-delta", type=float, default=1.0)
    parser.add_argument("--rotation-weight", type=float, default=0.05)
    return parser.parse_args()


def main():
    args = parse_args()
    rospy.init_node("pika_charuco_handeye_calib", anonymous=True)
    calibrator = CharucoHandeyeCalibrator(args)
    calibrator.run()


if __name__ == "__main__":
    main()
