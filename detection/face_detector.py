"""
SleepGuard — Face Landmark Detector

Wraps MediaPipe Face Landmarker (Tasks API) to detect facial landmarks
and compute bounding boxes for single-face monitoring.
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config.config import MODEL_PATH, DRAW_LANDMARKS
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceDetector:
    """Wraps MediaPipe Face Landmarker. Returns landmark set per frame."""

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        num_faces: int = 1,
        min_face_detection_confidence: float = 0.5,
        min_face_presence_confidence: float = 0.5,
    ):
        if not os.path.exists(model_path):
            logger.error("Face landmarker model file not found at: %s", model_path)
            raise FileNotFoundError(f"Model file not found: {model_path}")

        logger.info("Initializing FaceLandmarker with model: %s", model_path)
        base_options = python.BaseOptions(
            model_asset_path=model_path,
            delegate=python.BaseOptions.Delegate.CPU,
        )
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=num_faces,
            min_face_detection_confidence=min_face_detection_confidence,
            min_face_presence_confidence=min_face_presence_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame: np.ndarray) -> dict | None:
        """
        Run face landmark detection on a BGR frame.

        Returns structured dict with normalized and pixel landmarks, or None if no face found:
        {
            'landmarks': [(x, y, z), ...],       # normalized 0.0-1.0
            'pixel_landmarks': [(x, y, z), ...], # pixel coords
            'bbox': (x_min, y_min, width, height),
            'raw_landmarks': face_landmarks_obj,
        }
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        try:
            result = self.landmarker.detect(mp_image)
        except Exception as e:
            logger.error("Error during face landmark detection: %s", e)
            return None

        if not result or not result.face_landmarks:
            return None

        # Take first detected face
        face_landmarks = result.face_landmarks[0]
        norm_landmarks = [(lm.x, lm.y, lm.z) for lm in face_landmarks]
        pixel_landmarks = [(int(lm.x * w), int(lm.y * h), lm.z) for lm in face_landmarks]

        x_coords = [p[0] for p in pixel_landmarks]
        y_coords = [p[1] for p in pixel_landmarks]

        x_min, x_max = max(0, min(x_coords)), min(w, max(x_coords))
        y_min, y_max = max(0, min(y_coords)), min(h, max(y_coords))
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        return {
            'landmarks': norm_landmarks,
            'pixel_landmarks': pixel_landmarks,
            'bbox': bbox,
            'raw_landmarks': face_landmarks,
        }

    def draw_landmarks(self, frame: np.ndarray, detection_result: dict | None, draw_bbox: bool = True) -> np.ndarray:
        """Draw facial landmarks and bounding box in-place on a BGR frame."""
        if frame is None or detection_result is None:
            return frame

        pixel_landmarks = detection_result.get('pixel_landmarks', [])

        # Draw dots for landmarks directly in-place
        for x, y, _ in pixel_landmarks:
            cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

        # Draw bounding box directly in-place
        if draw_bbox and 'bbox' in detection_result:
            x, y, w, h = detection_result['bbox']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 191, 0), 2)

        return frame

    def close(self):
        """Release MediaPipe landmarker resources."""
        if hasattr(self, 'landmarker') and self.landmarker:
            self.landmarker.close()
            logger.info("FaceLandmarker closed.")
