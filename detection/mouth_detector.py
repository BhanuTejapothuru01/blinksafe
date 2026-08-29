"""
SleepGuard — Mouth / Yawn Detector

Uses Mouth Aspect Ratio (MAR) across consecutive frames to detect yawning.
"""

from config.config import MAR_THRESHOLD, MAR_CONSEC_FRAMES
from utils.calculations import calculate_mar
from utils.logger import get_logger

logger = get_logger(__name__)

# MediaPipe FaceLandmarker mouth landmark indices (8 points: 2 corners + 3 top/bottom pairs)
MOUTH_INDICES = [61, 81, 13, 311, 291, 402, 14, 178]


class MouthDetector:
    """Detects yawning using Mouth Aspect Ratio (MAR)."""

    def __init__(
        self,
        mar_threshold: float = MAR_THRESHOLD,
        consec_frames: int = MAR_CONSEC_FRAMES,
    ):
        self.threshold = mar_threshold
        self.consec_frames = consec_frames
        self.yawn_frame_count = 0

    def update(self, landmarks: list | None) -> dict:
        """
        Process facial landmarks and return mouth state dict.

        `landmarks`: List of (x, y, z) tuples (either normalized or pixel coords).
        Returns:
        {
            'mar': float,
            'yawning': bool,
            'consec_frames': int,
        }
        """
        if not landmarks or len(landmarks) < 468:
            return {
                'mar': 0.0,
                'yawning': False,
                'consec_frames': 0,
            }

        mouth_pts = [landmarks[i][:2] for i in MOUTH_INDICES]
        mar = calculate_mar(mouth_pts)

        if mar > self.threshold:
            self.yawn_frame_count += 1
        else:
            self.yawn_frame_count = 0

        is_yawning = self.yawn_frame_count >= self.consec_frames

        return {
            'mar': round(mar, 4),
            'yawning': is_yawning,
            'consec_frames': self.yawn_frame_count,
        }

    def reset(self):
        """Reset the frame counter state."""
        self.yawn_frame_count = 0
