"""
BlinkSafe — Emergency SOS Manager

Lightweight, timestamp-based 60-second SOS countdown manager designed for low-end
mobile hardware. Consumes zero CPU by using system time deltas rather than heavy loops.
"""

import time
import threading
from config.config import SOS_COUNTDOWN_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


class SOSManager:
    """Manages emergency SOS countdown when DANGER state is triggered."""

    def __init__(self, countdown_seconds: int = SOS_COUNTDOWN_SECONDS):
        self.countdown_seconds = countdown_seconds
        self.start_time = None
        self.target_time = None
        self._active = False
        self._triggered_sos = False
        self._lock = threading.Lock()

    def trigger(self, duration_seconds: int = None) -> bool:
        """Start or restart the 60-second SOS countdown."""
        duration = duration_seconds or self.countdown_seconds
        now = time.time()
        with self._lock:
            if self._active:
                return False  # Already active

            self.start_time = now
            self.target_time = now + duration
            self._active = True
            self._triggered_sos = False
            logger.warning("🚨 Emergency SOS Countdown Started (%d seconds)", duration)
            return True

    def cancel(self) -> bool:
        """Cancel active SOS countdown."""
        with self._lock:
            if not self._active:
                return False
            self._active = False
            self.start_time = None
            self.target_time = None
            self._triggered_sos = False
            logger.info("✅ SOS Countdown Canceled by user.")
            return True

    def get_status(self) -> dict:
        """Get current SOS status dict with remaining seconds."""
        with self._lock:
            if not self._active or self.target_time is None:
                return {
                    'active': False,
                    'remaining_seconds': 0,
                    'triggered': False,
                }

            now = time.time()
            remaining = max(0, int(round(self.target_time - now)))
            
            if remaining == 0 and not self._triggered_sos:
                self._triggered_sos = True
                logger.error("🚨 SOS COUNTDOWN EXPIRED! Emergency notification triggered.")

            return {
                'active': self._active,
                'remaining_seconds': remaining,
                'triggered': self._triggered_sos,
            }

    def reset(self):
        """Reset SOS manager state."""
        with self._lock:
            self.start_time = None
            self.target_time = None
            self._active = False
            self._triggered_sos = False
