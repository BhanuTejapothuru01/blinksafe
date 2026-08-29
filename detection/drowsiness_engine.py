"""
SleepGuard — Drowsiness Signal Fusion Engine

Fuses eye closure, yawning, and head pose signals into a single drowsiness score
and state machine (ALERT → DROWSY → DANGER) with state hysteresis.
"""

from config.config import (
    DROWSY_WEIGHTS,
    DROWSY_THRESHOLD,
    DANGER_THRESHOLD,
    STATE_HYSTERESIS_FRAMES,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DrowsinessEngine:
    """Fuses eye, mouth, and head signals into ALERT / DROWSY / DANGER states."""

    STATE_ALERT = 'ALERT'
    STATE_DROWSY = 'DROWSY'
    STATE_DANGER = 'DANGER'

    def __init__(
        self,
        weights: dict = DROWSY_WEIGHTS,
        drowsy_threshold: float = DROWSY_THRESHOLD,
        danger_threshold: float = DANGER_THRESHOLD,
        hysteresis_frames: int = STATE_HYSTERESIS_FRAMES,
    ):
        self.weights = weights
        self.drowsy_threshold = drowsy_threshold
        self.danger_threshold = danger_threshold
        self.hysteresis_frames = hysteresis_frames

        self.current_state = self.STATE_ALERT
        self.pending_state = self.STATE_ALERT
        self.pending_count = 0
        self.confidence = 0.0

    def update(self, eye_state: dict, mouth_state: dict, head_state: dict) -> dict:
        """
        Fuse individual indicator states into global state and confidence.

        `eye_state`: {'ear': float, 'closed': bool, ...}
        `mouth_state`: {'mar': float, 'yawning': bool, ...}
        `head_state`: {'pitch': float, 'yaw': float, 'nodding': bool, ...}

        Returns:
        {
            'state': 'ALERT' | 'DROWSY' | 'DANGER',
            'confidence': float (0.0 - 1.0),
            'eye_state': dict,
            'mouth_state': dict,
            'head_state': dict,
        }
        """
        # Calculate individual score contributions
        eye_score = 1.0 if eye_state.get('closed', False) else 0.0
        mouth_score = 1.0 if mouth_state.get('yawning', False) else 0.0
        head_score = 1.0 if head_state.get('nodding', False) else 0.0

        # Partial contributions based on values
        if not eye_score and eye_state.get('ear', 1.0) < 0.25:
            eye_score = (0.25 - eye_state['ear']) / 0.25

        if not mouth_score and mouth_state.get('mar', 0.0) > 0.5:
            mouth_score = min(1.0, (mouth_state['mar'] - 0.5) / 0.3)

        w_eye = self.weights.get('eye', 0.45)
        w_mouth = self.weights.get('mouth', 0.25)
        w_head = self.weights.get('head', 0.30)

        score = (eye_score * w_eye) + (mouth_score * w_mouth) + (head_score * w_head)
        self.confidence = round(float(min(1.0, max(0.0, score))), 2)

        # Determine target state
        if self.confidence >= self.danger_threshold or (eye_state.get('closed') and head_state.get('nodding')):
            target_state = self.STATE_DANGER
        elif self.confidence >= self.drowsy_threshold or eye_state.get('closed') or mouth_state.get('yawning') or head_state.get('nodding'):
            target_state = self.STATE_DROWSY
        else:
            target_state = self.STATE_ALERT

        # Hysteresis state transition
        if target_state == self.current_state:
            self.pending_state = self.current_state
            self.pending_count = 0
        else:
            if target_state == self.pending_state:
                self.pending_count += 1
            else:
                self.pending_state = target_state
                self.pending_count = 1

            # Immediate escalation to DANGER if severe, otherwise wait for hysteresis frames
            if (target_state == self.STATE_DANGER and self.confidence >= 0.85) or self.pending_count >= self.hysteresis_frames:
                logger.info("State transition: %s → %s (confidence=%.2f)", self.current_state, target_state, self.confidence)
                self.current_state = target_state
                self.pending_count = 0

        return {
            'state': self.current_state,
            'confidence': self.confidence,
            'eye_state': eye_state,
            'mouth_state': mouth_state,
            'head_state': head_state,
        }

    def reset(self):
        """Reset state machine to initial ALERT state."""
        self.current_state = self.STATE_ALERT
        self.pending_state = self.STATE_ALERT
        self.pending_count = 0
        self.confidence = 0.0
