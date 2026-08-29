"""
SleepGuard — Eye Closure Detector

Uses Eye Aspect Ratio (EAR) across consecutive frames to detect eye closure & microsleeps.
"""

from config.config import EAR_THRESHOLD, EAR_CONSEC_FRAMES
from utils.calculations import calculate_ear
from utils.logger import get_logger

logger = get_logger(__name__)

# MediaPipe FaceLandmarker eye landmark indices (6 points per eye)
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


class EyeDetector:
    """Detects sustained eye closure using Eye Aspect Ratio."""

    def __init__(
        self,
        ear_threshold: float = EAR_THRESHOLD,
        consec_frames: int = EAR_CONSEC_FRAMES,
    ):
        self.threshold = ear_threshold
        self.consec_frames = consec_frames
        self.closed_frame_count = 0

    def update(self, landmarks: list | None) -> dict:
        """
        Process facial landmarks and return eye state dict.

        `landmarks`: List of (x, y, z) tuples (either normalized or pixel coords).
        Returns:
        {
            'ear': float,
            'left_ear': float,
            'right_ear': float,
            'closed': bool,
            'consec_frames': int,
        }
        """
        if not landmarks or len(landmarks) < 468:
            return {
                'ear': 0.0,
                'left_ear': 0.0,
                'right_ear': 0.0,
                'closed': False,
                'consec_frames': 0,
            }

        left_pts = [landmarks[i][:2] for i in LEFT_EYE_INDICES]
        right_pts = [landmarks[i][:2] for i in RIGHT_EYE_INDICES]

        left_ear = calculate_ear(left_pts)
        right_ear = calculate_ear(right_pts)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < self.threshold:
            self.closed_frame_count += 1
        else:
            self.closed_frame_count = 0

        is_closed = self.closed_frame_count >= self.consec_frames

        return {
            'ear': round(avg_ear, 4),
            'left_ear': round(left_ear, 4),
            'right_ear': round(right_ear, 4),
            'closed': is_closed,
            'consec_frames': self.closed_frame_count,
        }

    def reset(self):
        """Reset the frame counter state."""
        self.closed_frame_count = 0
