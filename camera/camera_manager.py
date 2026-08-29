"""
SleepGuard — Camera Manager

OpenCV VideoCapture wrapper with graceful open / read / release,
camera-not-found handling, and MJPEG frame generation.
"""

import time
import cv2
import numpy as np
from threading import Lock
from config.config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET
from utils.logger import get_logger

logger = get_logger(__name__)


class CameraManager:
    """Thread-safe webcam wrapper that yields JPEG-encoded frames."""

    def __init__(self, camera_index=CAMERA_INDEX):
        self._camera_index = camera_index
        self._cap = None
        self._lock = Lock()
        self._frame_count = 0
        self._fps_start = time.time()
        self._current_fps = 0.0

    # ── lifecycle ────────────────────────────────────────────────────
    def open(self) -> bool:
        """Open the camera. Returns True on success."""
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return True

            logger.info("Opening camera index %d …", self._camera_index)
            self._cap = cv2.VideoCapture(self._camera_index)

            if not self._cap.isOpened():
                logger.error("Camera index %d could not be opened.", self._camera_index)
                self._cap = None
                return False

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self._cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)
            logger.info(
                "Camera opened — requested %dx%d @ %d FPS",
                FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET,
            )
            self._fps_start = time.time()
            self._frame_count = 0
            return True

    def release(self):
        """Release the camera resource."""
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
                logger.info("Camera released.")

    @property
    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    # ── frame reading ────────────────────────────────────────────────
    def read_frame(self):
        """
        Read a single BGR frame from the camera.
        Returns (success: bool, frame: np.ndarray | None).
        """
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return False, None
            ret, frame = self._cap.read()

        if ret:
            self._frame_count += 1
            elapsed = time.time() - self._fps_start
            if elapsed >= 1.0:
                self._current_fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_start = time.time()

        return ret, frame

    @property
    def fps(self) -> float:
        """Most recently measured FPS."""
        return self._current_fps

    # ── MJPEG generator ─────────────────────────────────────────────
    def generate_frames(self, process_frame_fn=None):
        """
        Generator that yields MJPEG multipart frames for Flask streaming.

        If `process_frame_fn` is provided it is called with the raw BGR frame
        and must return the (possibly annotated) BGR frame to encode.
        """
        if not self.open():
            # Yield a single "no camera" placeholder frame, then stop
            yield from self._no_camera_placeholder()
            return

        target_delay = 1.0 / FPS_TARGET if FPS_TARGET > 0 else 0

        while True:
            ret, frame = self.read_frame()
            if not ret:
                logger.warning("Frame read failed — camera may have disconnected.")
                yield from self._no_camera_placeholder()
                return

            # Optional per-frame processing (detection overlay, etc.)
            if process_frame_fn is not None:
                frame = process_frame_fn(frame)

            # Encode to JPEG
            ret_enc, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret_enc:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            )

            time.sleep(target_delay)

    # ── helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _no_camera_placeholder():
        """Yield a single JPEG frame with an error message."""
        placeholder = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        cv2.putText(
            placeholder,
            'Camera not available',
            (FRAME_WIDTH // 2 - 180, FRAME_HEIGHT // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2,
        )
        _, buf = cv2.imencode('.jpg', placeholder)
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
        )
