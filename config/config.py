"""
SleepGuard / BlinkSafe Configuration
All thresholds, camera settings, performance profiles, and alert parameters live here.
No magic numbers in detection files.
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ── Mobile & Adaptive Performance Profiles ──────────────────────────────────
# Options: 'LOW' (2 GB RAM target), 'BALANCED' (2-4 GB RAM), 'HIGH' (4+ GB RAM), 'AUTO'
PERFORMANCE_MODE = os.environ.get('PERFORMANCE_MODE', 'AUTO').upper()
LOW_END_MODE = os.environ.get('LOW_END_MODE', 'false').lower() in ('true', '1', 'yes') or PERFORMANCE_MODE == 'LOW'

# In LOW_END_MODE, process CV at 6-10 FPS while camera preview streams smoothly at 30 FPS
PROCESSING_FPS = 8 if LOW_END_MODE else 15 if PERFORMANCE_MODE == 'BALANCED' else 30

def get_scaled_consec_frames(base_frames: int, base_fps: float = 30.0, current_fps: float = PROCESSING_FPS) -> int:
    """Scale consecutive frame count so detection timing in seconds remains constant across FPS profiles."""
    if current_fps <= 0 or base_fps <= 0:
        return base_frames
    seconds = base_frames / base_fps
    return max(1, int(round(seconds * current_fps)))

# ── Camera Settings ────────────────────────────────────────────────────────
CAMERA_INDEX = 0
FRAME_WIDTH = 480 if LOW_END_MODE else 640
FRAME_HEIGHT = 360 if LOW_END_MODE else 480
FPS_TARGET = 30

# ── MediaPipe Model ──────────────────────────────────────────────────────
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'face_landmarker.task')
DRAW_LANDMARKS = not LOW_END_MODE  # Disable landmark overlay drawing on low-end 2 GB RAM devices to save CPU/GPU

# ── Eye Detection (EAR) ─────────────────────────────────────────────────
EAR_THRESHOLD = 0.21           # below this → eyes considered closed
EAR_CONSEC_FRAMES = get_scaled_consec_frames(15)  # ~0.5 seconds closure threshold

# ── Mouth / Yawn Detection (MAR) ────────────────────────────────────────
MAR_THRESHOLD = 0.75           # above this → mouth considered open (yawn)
MAR_CONSEC_FRAMES = get_scaled_consec_frames(10)  # ~0.33 seconds yawn threshold

# ── Head Pose ────────────────────────────────────────────────────────────
HEAD_PITCH_THRESHOLD = -15.0   # degrees — pitch below this → nodding
HEAD_YAW_THRESHOLD = 30.0      # degrees — yaw beyond this → looking away
HEAD_CONSEC_FRAMES = get_scaled_consec_frames(10)  # ~0.33 seconds threshold

# ── Drowsiness Engine ───────────────────────────────────────────────────
DROWSY_WEIGHTS = {
    'eye': 0.45,
    'mouth': 0.25,
    'head': 0.30,
}
DROWSY_THRESHOLD = 0.5         # combined score above this → DROWSY
DANGER_THRESHOLD = 0.75        # combined score above this → DANGER
STATE_HYSTERESIS_FRAMES = get_scaled_consec_frames(5)

# ── Alerts & SOS ─────────────────────────────────────────────────────────
ALARM_SOUND_PATH = os.path.join(BASE_DIR, 'static', 'sounds', 'alarm.wav')
ALARM_COOLDOWN_SECONDS = 10    # min seconds between alarm plays
SOS_COUNTDOWN_SECONDS = 60     # 60-second emergency SOS countdown timer

# ── Database ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, 'data', 'sleepguard.db')
SESSION_EXPORT_DIR = os.path.join(BASE_DIR, 'data', 'sessions')

# ── Logging ──────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'sleepguard.log')
LOG_LEVEL = 'DEBUG'
LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
LOG_BACKUP_COUNT = 3

# ── Flask ────────────────────────────────────────────────────────────────
FLASK_HOST = '0.0.0.0'
FLASK_PORT = int(os.environ.get('PORT', 5001))
FLASK_DEBUG = True
