"""
SleepGuard — Head Pose Estimator

Estimates head orientation (pitch, yaw, roll in degrees) using OpenCV solvePnP
to detect head nodding (nod-off) and side-facing distraction.
"""

import cv2
import numpy as np
from config.config import HEAD_PITCH_THRESHOLD, HEAD_YAW_THRESHOLD, HEAD_CONSEC_FRAMES
from utils.logger import get_logger

logger = get_logger(__name__)

# MediaPipe landmark indices for solvePnP face keypoints
# [Nose tip, Chin, Left eye left corner, Right eye right corner, Left mouth corner, Right mouth corner]
LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]

# Generic 3D facial model points (in mm)
MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),  # Left eye left corner
    (225.0, 170.0, -135.0),   # Right eye right corner
    (-150.0, -150.0, -125.0), # Left mouth corner
    (150.0, -150.0, -125.0),  # Right mouth corner
], dtype=np.float64)


class HeadPoseEstimator:
    """Estimates head pitch/yaw/roll from face landmarks using solvePnP."""

    def __init__(
        self,
        pitch_threshold: float = HEAD_PITCH_THRESHOLD,
        yaw_threshold: float = HEAD_YAW_THRESHOLD,
        consec_frames: int = HEAD_CONSEC_FRAMES,
    ):
        self.pitch_threshold = pitch_threshold
        self.yaw_threshold = yaw_threshold
        self.consec_frames = consec_frames
        self.nod_frame_count = 0

    def update(self, landmarks: list | None, frame_shape: tuple = (480, 640)) -> dict:
        """
        Process facial landmarks and compute pitch, yaw, roll angles in degrees.

        `landmarks`: List of (x, y, z) tuples (either normalized or pixel coords).
        `frame_shape`: (height, width) of the image frame.

        Returns:
        {
            'pitch': float (degrees, negative = looking down / nodding),
            'yaw': float (degrees, negative = left, positive = right),
            'roll': float (degrees, tilt),
            'nodding': bool,
            'consec_frames': int,
        }
        """
        if not landmarks or len(landmarks) < 300:
            return {
                'pitch': 0.0,
                'yaw': 0.0,
                'roll': 0.0,
                'nodding': False,
                'consec_frames': 0,
            }

        h, w = frame_shape[:2]

        # Extract 2D image points from landmarks
        image_points = []
        for idx in LANDMARK_INDICES:
            pt = landmarks[idx]
            # Convert normalized coords to pixel coords if necessary
            px = pt[0] * w if pt[0] <= 1.0 else pt[0]
            py = pt[1] * h if pt[1] <= 1.0 else pt[1]
            image_points.append([px, py])

        image_points = np.array(image_points, dtype=np.float64)

        # Camera intrinsic matrix setup
        focal_length = float(w)
        center = (w / 2.0, h / 2.0)
        camera_matrix = np.array([
            [focal_length, 0.0, center[0]],
            [0.0, focal_length, center[1]],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, _ = cv2.solvePnP(
            MODEL_POINTS_3D,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return {
                'pitch': 0.0,
                'yaw': 0.0,
                'roll': 0.0,
                'nodding': False,
                'consec_frames': 0,
            }

        # Convert rotation vector to matrix
        rmat, _ = cv2.Rodrigues(rvec)

        # Extract Euler angles (pitch, yaw, roll)
        sy = np.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
        singular = sy < 1e-6

        if not singular:
            x = np.arctan2(rmat[2, 1], rmat[2, 2])
            y = np.arctan2(-rmat[2, 0], sy)
            z = np.arctan2(rmat[1, 0], rmat[0, 0])
        else:
            x = np.arctan2(-rmat[1, 2], rmat[1, 1])
            y = np.arctan2(-rmat[2, 0], sy)
            z = 0.0

        pitch = np.degrees(x)
        yaw = np.degrees(y)
        roll = np.degrees(z)

        # Check for head nodding down (pitch below threshold) or excessive yaw
        is_nodding_down = pitch < self.pitch_threshold
        is_looking_away = abs(yaw) > self.yaw_threshold

        if is_nodding_down or is_looking_away:
            self.nod_frame_count += 1
        else:
            self.nod_frame_count = 0

        is_nodding = self.nod_frame_count >= self.consec_frames

        return {
            'pitch': round(float(pitch), 2),
            'yaw': round(float(yaw), 2),
            'roll': round(float(roll), 2),
            'nodding': is_nodding,
            'consec_frames': self.nod_frame_count,
        }

    def reset(self):
        """Reset head pose frame counter."""
        self.nod_frame_count = 0
