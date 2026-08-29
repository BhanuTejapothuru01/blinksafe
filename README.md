# 🛡️ SleepGuard / BlinkSafe — Real-Time Drowsiness Detection & Driver Identification

SleepGuard (BlinkSafe) is a real-time driver & user safety system that monitors driver alertness through **eye closure**, **yawning**, and **head pose** analysis, integrated with **Driver Identification** powered by **128D Face Embeddings** and **FAISS Vector Similarity Search**.

---

## 🏗️ System Architecture

SleepGuard operates using two concurrent, decoupled processing pipelines:

```
                    ┌─────────────────────────┐
                    │      Webcam Stream      │
                    └────────────┬────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │  MediaPipe Face Detector  │
                   └─────────────┬─────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌───────────────────────────────┐     ┌─────────────────────────────────┐
│     SAFETY PIPELINE (100%)    │     │  DRIVER RECOGNITION (Throttled) │
├───────────────────────────────┤     ├─────────────────────────────────┤
│ • Eye Aspect Ratio (EAR)      │     │ • 128D Face Embedding Extractor │
│ • Mouth Aspect Ratio (MAR)    │     │ • L2 Vector Normalization       │
│ • Head Pose (Pitch/Yaw/Roll)  │     │ • FAISS Vector Search (FlatIP)  │
│ • Drowsiness Fusion Engine    │     │ • Similarity Thresholding (0.45)│
│ • Alarm Playback              │     │ • Temporal Voting Window (5f)   │
│ • 60-Second SOS Countdown     │     │ • Driver Identity & Session     │
└──────────────┬────────────────┘     └────────────────┬────────────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                   ┌──────────────────────────────┐
                   │ SQLite Database & Reports    │
                   │ • sessions (with driver_id)  │
                   │ • drivers & face_embeddings  │
                   └──────────────────────────────┘
```

---

## 👤 Driver Registration & Recognition

### 1. Driver Registration Flow
1. Navigate to the **Dashboard** (`http://localhost:5001/`).
2. Click **+ Register Driver**.
3. Enter the driver's full **Name** and **Phone Number**.
4. The system opens the camera, detects facial landmarks, extracts a **128-dimensional L2-normalized embedding vector** using OpenCV's SFace model, and adds it to the FAISS index.
5. The mapping between vector ID, driver ID, and profile metadata is persisted to SQLite and disk.

### 2. Live Recognition & Multi-Frame Voting
- When monitoring starts, the system passes frame face regions to the recognition engine every $N$ frames (default: every 5 frames).
- Face embeddings are searched against the FAISS `IndexFlatIP` vector index.
- **Strict Thresholding**: If the cosine similarity score is below `0.45`, the face is categorized as `UNKNOWN_DRIVER` (preventing false nearest-neighbor assignments).
- **Temporal Voting Window**: The recognizer maintains a 5-frame sliding window. A driver's identity is confirmed only after consistent matches across the voting window, preventing single-frame glitches or false switches.

---

## ⚡ Features

- 👤 **Driver Identification**: Biometric face embedding recognition via FAISS vector search
- 📹 **Live MJPEG Stream**: Webcam monitoring with real-time UI status overlays
- 👁️ **Eye Aspect Ratio (EAR)**: Micro-sleep and blink detection
- 🥱 **Mouth Aspect Ratio (MAR)**: Yawn frequency monitoring
- 🔄 **Head Pose Estimation**: Pitch/yaw nod-off detection
- 🧠 **Weighted Signal Fusion**: Real-time state classification (`ALERT` → `DROWSY` → `DANGER`)
- 🔊 **Audio Alarm & SOS**: Loud alert playback on `DANGER` + 60-second emergency SOS countdown
- 📊 **Session Reports**: Interactive timelines with Chart.js, safety index, and driver binding
- 📱 **Mobile Ready**: Adaptive performance modes for 2 GB RAM budget devices

---

## 🚀 Quick Start

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

---

## ⚙️ Threshold Configuration

All detection and recognition thresholds live in [`config/config.py`](config/config.py):

| Parameter | Default | Description |
|---|---|---|
| `EAR_THRESHOLD` | `0.21` | EAR below this → eyes closed |
| `MAR_THRESHOLD` | `0.75` | MAR above this → mouth open (yawn) |
| `HEAD_PITCH_THRESHOLD` | `-15°` | Pitch below this → head nodding |
| `RECOGNITION_SIMILARITY_THRESHOLD` | `0.45` | Cosine similarity threshold for FAISS vector search |
| `RECOGNITION_FRAME_INTERVAL` | `5` | Recognition processing interval (frames) |
| `RECOGNITION_VOTING_WINDOW` | `5` | Sliding frame window count for temporal identity verification |

---

## 🔒 Privacy & Biometric Security

- **No Raw Face Images**: SleepGuard does NOT store raw camera images or video frames.
- **Local FAISS Indexing**: Biometric face embeddings are kept 100% local inside `data/faiss/drivers.index`.
- **Git Protection**: `.gitignore` explicitly excludes `.index` and `.json` biometric vector files from repository commits.

---

## 📁 Project Structure

```
blinksafe/
├── start.py                   # Master cross-platform launcher (Auto ML model fetcher)
├── app.py                     # Flask entrypoint & API routes
├── requirements.txt           # Python dependencies (includes faiss-cpu)
├── config/config.py           # Thresholds, model paths, and FAISS settings
├── recognition/               # Driver Identification & FAISS Package
│   ├── face_embedding.py      # SFace 128D ONNX embedding extractor
│   ├── faiss_manager.py       # FAISS IndexFlatIP vector manager & persistence
│   ├── face_recognizer.py     # Multi-frame temporal voting & driver change detector
│   └── driver_registry.py     # Driver registration & SQLite CRUD coordinator
├── detection/                 # Safety detection modules (EAR, MAR, Head Pose)
│   ├── face_detector.py       # MediaPipe face landmarker
│   ├── eye_detector.py        # EAR-based eye closure
│   ├── mouth_detector.py      # MAR-based yawn detection
│   ├── head_pose.py           # solvePnP head pose
│   └── drowsiness_engine.py   # Signal fusion engine
├── alerts/alarm.py            # Alarm audio player
├── database/                  # SQLite persistence
│   ├── database.py            # Connection & schema migrations
│   └── models.py              # Driver, Embedding, Session, & Event data models
├── reports/report_generator.py # Session report builder with driver binding
├── utils/                     # SOS manager & rotating file logger
├── templates/                 # Jinja2 HTML templates
├── static/                    # CSS, JS, audio assets
├── tests/                     # Pytest test suite (37 unit tests)
├── models/                    # MediaPipe & OpenCV SFace ONNX models
└── data/                      # SQLite DB & persistent FAISS index storage
```

---

## 🧪 Running Tests

Run the complete test suite (37 unit tests):

```bash
pytest tests/ -v
```

---

## 📄 License

MIT
