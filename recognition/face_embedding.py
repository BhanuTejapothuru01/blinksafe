"""
BlinkSafe — Face Embedding Extractor

Isolated face embedding generation layer.
Uses OpenCV FaceRecognizerSF (SFace 128D ONNX model) with facial affine alignment
and float32 L2 normalization for FAISS vector indexing and search.
"""

import os
import cv2
import numpy as np
import faiss

from config.config import SFACE_MODEL_PATH, RECOGNITION_EMBEDDING_DIM
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceEmbeddingExtractor:
    """Generates 128-dimensional L2-normalized face embedding vectors using SFace."""

    def __init__(self, model_path: str = SFACE_MODEL_PATH):
        self.model_path = model_path
        self.dim = RECOGNITION_EMBEDDING_DIM
        self.recognizer = None
        self._load_model()

    def _load_model(self):
        """Initialize OpenCV FaceRecognizerSF model if file exists."""
        if not os.path.exists(self.model_path) or os.path.getsize(self.model_path) < 1000000:
            logger.warning("SFace ONNX model missing or incomplete at %s.", self.model_path)
            self.recognizer = None
            return

        try:
            if hasattr(cv2, 'FaceRecognizerSF'):
                self.recognizer = cv2.FaceRecognizerSF.create(self.model_path, "")
                logger.info("OpenCV FaceRecognizerSF model loaded successfully from %s", self.model_path)
            else:
                logger.error("cv2.FaceRecognizerSF is not supported in current OpenCV build.")
                self.recognizer = None
        except Exception as e:
            logger.error("Failed to load FaceRecognizerSF model: %s", e)
            self.recognizer = None

    def extract_embedding(
        self,
        frame: np.ndarray,
        bbox: tuple | None = None,
        landmarks: list | None = None,
    ) -> np.ndarray | None:
        """
        Extract a normalized 128D face embedding vector from a BGR image frame.
        Applies identical facial crop & affine alignment during registration and recognition.

        Parameters:
            frame: Full BGR OpenCV frame.
            bbox: Optional (x, y, w, h) bounding box of detected face.
            landmarks: Optional pixel landmark coordinates [(x, y, z), ...].

        Returns:
            1D float32 numpy array of shape (128,) with L2 norm = 1.0, or None if extraction fails.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]

        # 1. Align face using eye landmarks or crop box
        aligned_face = self._align_face(frame, bbox=bbox, landmarks=landmarks)
        if aligned_face is None or aligned_face.size == 0:
            return None

        # 2. Extract feature vector with SFace ONNX model
        if self.recognizer is not None:
            try:
                feature = self.recognizer.feature(aligned_face)
                if feature is not None and feature.size > 0:
                    vec = feature.flatten().astype(np.float32)
                    return self.normalize_embedding(vec)
            except Exception as e:
                logger.warning("SFace feature extraction exception: %s", e)

        # Fallback feature vector if ONNX model is unavailable
        return self._fallback_embedding(aligned_face)

    def _align_face(
        self,
        frame: np.ndarray,
        bbox: tuple | None = None,
        landmarks: list | None = None,
    ) -> np.ndarray | None:
        """
        Align face by rotating eye centers horizontally and scaling to standard 112x112 BGR image.
        Ensures 100% identical preprocessing for registration and recognition.
        """
        h, w = frame.shape[:2]

        # Extract left and right eye centers if MediaPipe pixel landmarks provided
        left_eye_center = None
        right_eye_center = None

        if landmarks and len(landmarks) >= 468:
            try:
                # MediaPipe landmark indices for eye centers:
                # Left eye center: index 468 or average of (33, 133, 159, 145)
                # Right eye center: index 473 or average of (362, 263, 386, 374)
                l_pts = [landmarks[33], landmarks[133], landmarks[159], landmarks[145]]
                r_pts = [landmarks[362], landmarks[263], landmarks[386], landmarks[374]]
                left_eye_center = (
                    sum(p[0] for p in l_pts) / len(l_pts),
                    sum(p[1] for p in l_pts) / len(l_pts),
                )
                right_eye_center = (
                    sum(p[0] for p in r_pts) / len(r_pts),
                    sum(p[1] for p in r_pts) / len(r_pts),
                )
            except Exception:
                left_eye_center = None
                right_eye_center = None

        if left_eye_center and right_eye_center:
            dx = right_eye_center[0] - left_eye_center[0]
            dy = right_eye_center[1] - left_eye_center[1]
            angle = np.degrees(np.arctan2(dy, dx))
            center = (
                int((left_eye_center[0] + right_eye_center[0]) / 2),
                int((left_eye_center[1] + right_eye_center[1]) / 2),
            )
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_CUBIC)
        else:
            rotated = frame

        # Crop face region with 15% margin
        if bbox is not None and len(bbox) == 4:
            bx, by, bw, bh = bbox
            margin_x = int(bw * 0.15)
            margin_y = int(bh * 0.15)
            x1 = max(0, bx - margin_x)
            y1 = max(0, by - margin_y)
            x2 = min(w, bx + bw + margin_x)
            y2 = min(h, by + bh + margin_y)
            face_crop = rotated[y1:y2, x1:x2]
        else:
            face_crop = rotated

        if face_crop is None or face_crop.size == 0 or face_crop.shape[0] < 20 or face_crop.shape[1] < 20:
            return None

        # Resize to 112x112
        return cv2.resize(face_crop, (112, 112), interpolation=cv2.INTER_AREA)

    def normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Ensure embedding vector is float32 and L2-normalized to unit length (norm=1.0)."""
        vec = np.asarray(embedding, dtype=np.float32).flatten()
        faiss_matrix = vec.reshape(1, len(vec))
        faiss.normalize_L2(faiss_matrix)
        vec = faiss_matrix.flatten()
        return vec

    def _fallback_embedding(self, face_img: np.ndarray) -> np.ndarray:
        """Fallback feature vector if ONNX model is unavailable."""
        hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
        hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256]).flatten()
        
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        resized_gray = cv2.resize(gray, (8, 4)).flatten().astype(np.float32)
        
        concat = np.concatenate([hist_h, hist_s, hist_v, resized_gray])
        if len(concat) < self.dim:
            concat = np.pad(concat, (0, self.dim - len(concat)))
        elif len(concat) > self.dim:
            concat = concat[:self.dim]
            
        return self.normalize_embedding(concat)
