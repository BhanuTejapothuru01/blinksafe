"""
SleepGuard Configuration
All thresholds, camera settings, and alert parameters live here.
No magic numbers in detection files.
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# ── Camera ────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_TARGET = 30

# ── MediaPipe Model ──────────────────────────────────────────────────────
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'face_landmarker.task')
DRAW_LANDMARKS = True          # toggle landmark overlay on stream

# ── Eye Detection (EAR) ─────────────────────────────────────────────────
EAR_THRESHOLD = 0.21           # below this → eyes considered closed
EAR_CONSEC_FRAMES = 15         # sustained frames before flagging closure

# ── Mouth / Yawn Detection (MAR) ────────────────────────────────────────
MAR_THRESHOLD = 0.75           # above this → mouth considered open (yawn)
MAR_CONSEC_FRAMES = 10         # sustained frames before flagging yawn

# ── Head Pose ────────────────────────────────────────────────────────────
HEAD_PITCH_THRESHOLD = -15.0   # degrees — pitch below this → nodding
HEAD_YAW_THRESHOLD = 30.0      # degrees — yaw beyond this → looking away
HEAD_CONSEC_FRAMES = 10        # sustained frames before flagging

# ── Drowsiness Engine ───────────────────────────────────────────────────
DROWSY_WEIGHTS = {
    'eye': 0.45,
    'mouth': 0.25,
    'head': 0.30,
}
DROWSY_THRESHOLD = 0.5         # combined score above this → DROWSY
DANGER_THRESHOLD = 0.75        # combined score above this → DANGER
STATE_HYSTERESIS_FRAMES = 5    # frames a state must hold before transition

# ── Alerts ───────────────────────────────────────────────────────────────
ALARM_SOUND_PATH = os.path.join(BASE_DIR, 'static', 'sounds', 'alarm.wav')
ALARM_COOLDOWN_SECONDS = 10    # min seconds between alarm plays

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
