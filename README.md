# 🛡️ SleepGuard / BlinkSafe — Real-Time Drowsiness Detection

SleepGuard (BlinkSafe) is a real-time driver & user drowsiness detection system that uses your webcam to monitor alertness through **eye closure**, **yawning**, and **head pose** analysis.

## Features

- 📹 Live webcam monitoring via MJPEG stream
- 👁️ Eye Aspect Ratio (EAR) detection for blink & microsleep tracking
- 🥱 Mouth Aspect Ratio (MAR) for yawn detection
- 🔄 Head pose estimation (pitch/yaw) for nod-off detection
- 🧠 Weighted drowsiness fusion engine (ALERT → DROWSY → DANGER)
- 🔊 Audible alarm on DANGER state
- 📊 Session logging with SQLite + visual reports with Chart.js
- 🌙 Modern dark-theme dashboard UI

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/BhanuTejapothuru01/blinksafe.git
cd blinksafe
```

### 2. Run with One Command

#### 🍏 macOS / 🐧 Linux
```bash
chmod +x start.sh
./start.sh
```

#### 💻 Windows
Double-click `start.bat` or run in Command Prompt:
```cmd
start.bat
```
Or in PowerShell:
```powershell
.\start.ps1
```

---

### ⚡ What the Startup Script Does Automatically:
1. **Checks Python 3**: Verifies that Python 3 is installed.
2. **Creates & Activates Virtual Environment**: Automatically initializes `venv/` if missing.
3. **Installs Dependencies**: Upgrades pip and installs missing dependencies from `requirements.txt` (skips reinstall on subsequent runs).
4. **Verifies Imports**: Ensures `flask`, `opencv-python`, `mediapipe`, and `numpy` import properly.
5. **Downloads MediaPipe Assets**: Automatically fetches `face_landmarker.task` from Google storage if missing.
6. **Creates Required Directories**: Ensures `models/`, `data/`, `data/sessions/`, `logs/`, `reports/` exist.
7. **Resolves Port Conflicts**: Checks port `5001` and automatically assigns an available port if occupied.
8. **Launches Server**: Starts Flask and displays project Dashboard URLs.

### 3. Open in Browser

Once started, access the project URLs:
- **Dashboard**: [http://localhost:5001/](http://localhost:5001/) — Overview & session history
- **Live Monitor**: [http://localhost:5001/session](http://localhost:5001/session) — Live webcam feed & detection controls

---

### Manual Setup (Alternative)

If you prefer manual setup:

1. **Virtual Environment & Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download Model**:
   ```bash
   curl -L -o models/face_landmarker.task \
     "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
   ```

3. **Start Application**:
   ```bash
   python3 app.py
   ```

---

## Threshold Configuration

All detection thresholds are configured in [`config/config.py`](config/config.py):

| Parameter | Default | Description |
|---|---|---|
| `CAMERA_INDEX` | `0` | Webcam device index |
| `EAR_THRESHOLD` | `0.21` | EAR below this → eyes closed |
| `EAR_CONSEC_FRAMES` | `15` | Frames of closure before alert |
| `MAR_THRESHOLD` | `0.75` | MAR above this → yawning |
| `HEAD_PITCH_THRESHOLD` | `-15°` | Pitch below this → nodding |
| `ALARM_COOLDOWN_SECONDS` | `10` | Min seconds between alarms |
| `FLASK_PORT` | `5001` | Server web port |

## Project Structure

```
blinksafe/
├── start.py                   # Master cross-platform launcher
├── start.sh                   # macOS / Linux startup script
├── start.bat                  # Windows Command Prompt startup script
├── start.ps1                  # Windows PowerShell startup script
├── app.py                     # Flask entrypoint & API routes
├── requirements.txt           # Core Python dependencies
├── package.json               # npm scripts configuration
├── config/config.py           # All thresholds & settings
├── camera/camera_manager.py   # OpenCV webcam wrapper
├── detection/                 # Detection modules
│   ├── face_detector.py       # MediaPipe face landmarker
│   ├── eye_detector.py        # EAR-based eye closure
│   ├── mouth_detector.py      # MAR-based yawn detection
│   ├── head_pose.py           # solvePnP head pose
│   └── drowsiness_engine.py   # Signal fusion engine
├── alerts/alarm.py            # Alarm .wav playback (cross-platform)
├── database/                  # SQLite persistence
│   ├── database.py            # Connection & CRUD
│   └── models.py              # Session & Event models
├── reports/report_generator.py # Report data builder
├── utils/                     # Shared utilities
│   ├── calculations.py        # EAR/MAR math
│   ├── logger.py              # Rotating file logger
│   └── helpers.py             # General helpers
├── templates/                 # Jinja2 HTML templates
├── static/                    # CSS, JS, audio assets
├── tests/                     # Pytest suite
├── models/                    # MediaPipe model storage
└── data/                      # SQLite DB & session exports
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## License

MIT
