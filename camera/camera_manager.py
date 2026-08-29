"""
SleepGuard — Camera Manager

High-performance, thread-safe webcam wrapper with background frame capture thread,
stale frame discarding for zero-latency streaming, and MJPEG frame generation.
"""

import sys
import time
import threading
import cv2
import numpy as np
from config.config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET, PROCESSING_FPS, LOW_END_MODE
from utils.logger import get_logger

logger = get_logger(__name__)


class CameraManager:
    """
    Thread-safe webcam wrapper featuring a background capture thread to
    eliminate hardware buffer queue backlog and ensure real-time low latency.
    """

    def __init__(self, camera_index=CAMERA_INDEX):
        self._camera_index = camera_index
        self._cap = None
        self._lock = threading.Lock()
        self._latest_frame = None
        self._frame_count = 0
        self._fps_start = time.time()
        self._current_fps = 0.0
        self._thread = None
        self._running = False

    # ── lifecycle ────────────────────────────────────────────────────
    def open(self) -> bool:
        """Open the camera and start background capture thread. Returns True on success."""
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return True

            logger.info("Opening camera index %d …", self._camera_index)

            # On Windows, attempt CAP_DSHOW backend first for fast, low-latency capture
            if sys.platform == 'win32':
                try:
                    self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
                except Exception:
                    self._cap = cv2.VideoCapture(self._camera_index)
            else:
                self._cap = cv2.VideoCapture(self._camera_index)

            if not self._cap or not self._cap.isOpened():
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
            self._running = True

            # Launch background capture thread to drain hardware camera buffer continuously
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            return True

    def _capture_loop(self):
        """Background thread loop that continuously fetches hardware camera frames."""
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                time.sleep(0.01)
                continue

            ret, frame = self._cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._latest_frame = frame
                    self._frame_count += 1
                    elapsed = time.time() - self._fps_start
                    if elapsed >= 1.0:
                        self._current_fps = self._frame_count / elapsed
                        self._frame_count = 0
                        self._fps_start = time.time()
            else:
                time.sleep(0.005)

    def release(self):
        """Release the camera resource and stop background capture thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
                self._latest_frame = None
                logger.info("Camera released.")

    @property
    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened() and self._running

    # ── frame reading ────────────────────────────────────────────────
    def read_frame(self):
        """
        Read the latest real-time BGR frame (zero-latency).
        Returns (success: bool, frame: np.ndarray | None).
        """
        with self._lock:
            if not self._running or self._latest_frame is None:
                return False, None
            # Return copy of reference to latest frame
            return True, self._latest_frame

    @property
    def fps(self) -> float:
        """Most recently measured camera capture FPS."""
        return self._current_fps

    # ── MJPEG generator ─────────────────────────────────────────────
    def generate_frames(self, process_frame_fn=None):
        """
        Generator that yields MJPEG multipart frames for Flask streaming.
        Prioritizes the most recent frame and eliminates sleep latency backlog.
        """
        if not self.open():
            yield from self._no_camera_placeholder()
            return

        target_delay = 1.0 / FPS_TARGET if FPS_TARGET > 0 else 0.033
        inference_interval = 1.0 / PROCESSING_FPS if (LOW_END_MODE and PROCESSING_FPS > 0) else 0.0
        last_inference_time = 0.0

        while self._running:
            t0 = time.time()
            ret, frame = self.read_frame()

            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Process frame if not throttled by low-end mode
            if process_frame_fn is not None:
                if not LOW_END_MODE or (t0 - last_inference_time >= inference_interval):
                    frame = process_frame_fn(frame)
                    last_inference_time = t0

            # Encode to JPEG
            ret_enc, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret_enc:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            )

            # Calculate processing time and sleep only remaining interval (if any)
            elapsed = time.time() - t0
            sleep_time = target_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

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
