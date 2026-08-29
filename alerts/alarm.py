"""
BlinkSafe — Alarm Manager

Non-blocking audio alert playback for DANGER state with cooldown handling and direct test support.
"""

import os
import sys
import time
import subprocess
import threading
from config.config import ALARM_SOUND_PATH, ALARM_COOLDOWN_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


class AlarmManager:
    """Plays alarm sound on DANGER state with configurable cooldown."""

    def __init__(
        self,
        sound_path: str = ALARM_SOUND_PATH,
        cooldown_seconds: float = ALARM_COOLDOWN_SECONDS,
    ):
        self.sound_path = sound_path
        self.cooldown_seconds = cooldown_seconds
        self.last_played = 0.0
        self._lock = threading.Lock()

    def trigger(self, force: bool = False) -> bool:
        """
        Attempt to play alarm sound.
        Returns True if sound was played, False if suppressed by cooldown.
        """
        now = time.time()
        with self._lock:
            if not force and (now - self.last_played < self.cooldown_seconds):
                logger.info("ALARM SUPPRESSED BY COOLDOWN (%.1fs remaining)", self.cooldown_seconds - (now - self.last_played))
                return False

            if not os.path.exists(self.sound_path):
                logger.warning("Alarm sound file not found at: %s", self.sound_path)
                return False

            self.last_played = now
            logger.warning("🚨 ALARM TRIGGERED! Executing sound playback: %s", self.sound_path)

            # Play in background thread so frame rate is never blocked
            thread = threading.Thread(target=self._play_sound, daemon=True)
            thread.start()
            return True

    def _play_sound(self):
        """Internal audio playback helper using platform default utilities."""
        try:
            if sys.platform == 'darwin':  # macOS
                logger.info("🔊 macOS afplay executing sound file: %s", self.sound_path)
                res = subprocess.run(['afplay', self.sound_path], check=False, capture_output=True)
                if res.returncode != 0:
                    logger.error("afplay failed with returncode %d: %s", res.returncode, res.stderr.decode('utf-8', errors='ignore'))
                else:
                    logger.info("afplay finished playing sound successfully.")
            elif sys.platform.startswith('linux'):
                logger.info("🔊 Linux aplay executing sound file: %s", self.sound_path)
                subprocess.run(['aplay', self.sound_path], check=False)
            elif sys.platform == 'win32':
                logger.info("🔊 Windows winsound playing sound file: %s", self.sound_path)
                import winsound
                winsound.PlaySound(self.sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            logger.error("Error playing alarm sound: %s", e)

    def reset(self):
        """Reset cooldown timer."""
        with self._lock:
            self.last_played = 0.0
