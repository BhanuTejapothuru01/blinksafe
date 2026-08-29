"""
SleepGuard — Main Flask Application

Routes:
  /              → Dashboard (index.html)
  /session       → Live monitoring page (session.html)
  /report/<id>   → Session report page (report.html)
  /video_feed    → MJPEG stream from webcam with live detection overlays
  /api/status    → JSON live detection metrics
  /api/sessions  → Past sessions summary list
  /api/session/start → Start new monitoring session
  /api/session/stop  → Stop active session
  /api/report/<id> → Session report data endpoint
"""

import time
from datetime import datetime
import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request

from camera.camera_manager import CameraManager
from config.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, DRAW_LANDMARKS
from utils.logger import get_logger

from detection.face_detector import FaceDetector
from detection.eye_detector import EyeDetector
from detection.mouth_detector import MouthDetector
from detection.head_pose import HeadPoseEstimator
from detection.drowsiness_engine import DrowsinessEngine
from alerts.alarm import AlarmManager
from database.database import DatabaseManager
from reports.report_generator import ReportGenerator

logger = get_logger(__name__)

# ── App & Core Services ──────────────────────────────────────────────────
app = Flask(__name__)
camera = CameraManager()

try:
    face_detector = FaceDetector()
except Exception as e:
    logger.error("Failed to initialize FaceDetector: %s", e)
    face_detector = None

eye_detector = EyeDetector()
mouth_detector = MouthDetector()
head_pose_estimator = HeadPoseEstimator()
drowsiness_engine = DrowsinessEngine()
alarm_manager = AlarmManager()
db_manager = DatabaseManager()
report_generator = ReportGenerator(db_manager)

# ── Global Live State ────────────────────────────────────────────────────
session_state = {
    'active': False,
    'session_id': None,
    'start_time': None,
    'drowsy_count': 0,
    'danger_count': 0,
    'yawn_count': 0,
    'blink_count': 0,
    'nod_count': 0,
    'ear_samples': [],
    'mar_samples': [],
    'last_logged_state': 'ALERT',
    'last_eye_closed': False,
    'last_yawning': False,
    'last_nodding': False,
}

latest_frame_metrics = {
    'state': 'ALERT',
    'confidence': 0.0,
    'ear': 0.0,
    'mar': 0.0,
    'pitch': 0.0,
    'yaw': 0.0,
    'roll': 0.0,
    'eye_closed': False,
    'yawning': False,
    'nodding': False,
}


def process_frame(frame: np.ndarray) -> np.ndarray:
    """Run detection pipeline on BGR webcam frame and draw UI overlay."""
    global latest_frame_metrics

    if frame is None or face_detector is None:
        return frame

    h, w = frame.shape[:2]
    detection = face_detector.detect(frame)

    if detection and detection.get('landmarks'):
        landmarks = detection['landmarks']

        # Run module detectors
        eye_res = eye_detector.update(landmarks)
        mouth_res = mouth_detector.update(landmarks)
        head_res = head_pose_estimator.update(landmarks, frame_shape=(h, w))
        fused = drowsiness_engine.update(eye_res, mouth_res, head_res)

        # Update latest frame metrics
        latest_frame_metrics = {
            'state': fused['state'],
            'confidence': fused['confidence'],
            'ear': eye_res['ear'],
            'mar': mouth_res['mar'],
            'pitch': head_res['pitch'],
            'yaw': head_res['yaw'],
            'roll': head_res['roll'],
            'eye_closed': eye_res['closed'],
            'yawning': mouth_res['yawning'],
            'nodding': head_res['nodding'],
        }

        # Trigger audio alarm on DANGER state
        if fused['state'] == DrowsinessEngine.STATE_DANGER:
            alarm_manager.trigger()

        # Session tracking & DB event logging
        if session_state['active'] and session_state['session_id']:
            sess_id = session_state['session_id']

            session_state['ear_samples'].append(eye_res['ear'])
            session_state['mar_samples'].append(mouth_res['mar'])

            # Log blinks / eye closure transition
            if eye_res['closed'] and not session_state['last_eye_closed']:
                session_state['blink_count'] += 1
            session_state['last_eye_closed'] = eye_res['closed']

            # Log yawns
            if mouth_res['yawning'] and not session_state['last_yawning']:
                session_state['yawn_count'] += 1
                db_manager.log_event(sess_id, 'YAWN', fused['confidence'], eye_res['ear'], mouth_res['mar'], head_res['pitch'], head_res['yaw'])
            session_state['last_yawning'] = mouth_res['yawning']

            # Log head nods
            if head_res['nodding'] and not session_state['last_nodding']:
                session_state['nod_count'] += 1
            session_state['last_nodding'] = head_res['nodding']

            # Log state transition events
            curr_state = fused['state']
            if curr_state != session_state['last_logged_state']:
                if curr_state == DrowsinessEngine.STATE_DROWSY:
                    session_state['drowsy_count'] += 1
                    db_manager.log_event(sess_id, 'DROWSY', fused['confidence'], eye_res['ear'], mouth_res['mar'], head_res['pitch'], head_res['yaw'])
                elif curr_state == DrowsinessEngine.STATE_DANGER:
                    session_state['danger_count'] += 1
                    db_manager.log_event(sess_id, 'DANGER', fused['confidence'], eye_res['ear'], mouth_res['mar'], head_res['pitch'], head_res['yaw'])

                session_state['last_logged_state'] = curr_state

        # Draw overlays
        if DRAW_LANDMARKS:
            frame = face_detector.draw_landmarks(frame, detection, draw_bbox=True)

        # Draw State Banner overlay at top
        state = fused['state']
        color = (0, 220, 0) if state == 'ALERT' else ((0, 165, 255) if state == 'DROWSY' else (0, 0, 255))
        cv2.rectangle(frame, (0, 0), (w, 40), (15, 23, 42), -1)
        cv2.putText(frame, f"STATE: {state}", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        cv2.putText(
            frame,
            f"EAR: {eye_res['ear']:.2f} | MAR: {mouth_res['mar']:.2f} | Pitch: {head_res['pitch']:.1f}deg",
            (w - 380, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )

    else:
        # No face detected
        latest_frame_metrics['state'] = 'NO FACE'
        cv2.rectangle(frame, (0, 0), (w, 40), (15, 23, 42), -1)
        cv2.putText(frame, "STATE: NO FACE DETECTED", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 120, 120), 2, cv2.LINE_AA)

    return frame


# ── Page Routes ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/session')
def session_page():
    return render_template('session.html')


@app.route('/report/<int:session_id>')
def report_page(session_id):
    return render_template('report.html', session_id=session_id)


# ── Video Stream Route ───────────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    return Response(
        camera.generate_frames(process_frame_fn=process_frame),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )


# ── API Endpoints ────────────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    return jsonify({
        **latest_frame_metrics,
        'fps': round(camera.fps, 1),
        'session_active': session_state['active'],
        'session_id': session_state['session_id'],
        'blink_count': session_state['blink_count'],
        'yawn_count': session_state['yawn_count'],
        'nod_count': session_state['nod_count'],
        'drowsy_count': session_state['drowsy_count'],
        'danger_count': session_state['danger_count'],
    })


@app.route('/api/session/start', methods=['POST'])
def api_start_session():
    if session_state['active']:
        return jsonify({'status': 'already_active', 'session_id': session_state['session_id']})

    session_id = db_manager.start_session()
    session_state['active'] = True
    session_state['session_id'] = session_id
    session_state['start_time'] = time.time()
    session_state['drowsy_count'] = 0
    session_state['danger_count'] = 0
    session_state['yawn_count'] = 0
    session_state['blink_count'] = 0
    session_state['nod_count'] = 0
    session_state['ear_samples'] = []
    session_state['mar_samples'] = []
    session_state['last_logged_state'] = 'ALERT'

    drowsiness_engine.reset()
    eye_detector.reset()
    mouth_detector.reset()
    head_pose_estimator.reset()
    alarm_manager.reset()

    return jsonify({'status': 'started', 'session_id': session_id})


@app.route('/api/session/stop', methods=['POST'])
def api_stop_session():
    if not session_state['active'] or not session_state['session_id']:
        return jsonify({'status': 'no_active_session'}), 400

    session_id = session_state['session_id']
    duration_sec = round(time.time() - (session_state['start_time'] or time.time()), 1)

    avg_ear = float(np.mean(session_state['ear_samples'])) if session_state['ear_samples'] else 0.0
    avg_mar = float(np.mean(session_state['mar_samples'])) if session_state['mar_samples'] else 0.0

    summary = {
        'duration_seconds': duration_sec,
        'drowsy_count': session_state['drowsy_count'],
        'danger_count': session_state['danger_count'],
        'yawn_count': session_state['yawn_count'],
        'blink_count': session_state['blink_count'],
        'avg_ear': round(avg_ear, 3),
        'avg_mar': round(avg_mar, 3),
    }

    db_manager.end_session(session_id, summary)

    session_state['active'] = False
    session_state['session_id'] = None

    return jsonify({'status': 'stopped', 'session_id': session_id, 'redirect_url': f'/report/{session_id}'})


@app.route('/api/sessions')
def api_sessions():
    sessions = db_manager.get_all_sessions(limit=30)
    return jsonify({'sessions': sessions})


@app.route('/api/report/<int:session_id>')
def api_report(session_id):
    report_data = report_generator.generate(session_id)
    return jsonify(report_data)


# ── Entrypoint ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("Starting SleepGuard server on %s:%s", FLASK_HOST, FLASK_PORT)
    print("\n" + "=" * 50)
    print("  🛡️  SleepGuard / BlinkSafe Server Started")
    print(f"  👉 Dashboard:    http://localhost:{FLASK_PORT}/")
    print(f"  👉 Live Monitor: http://localhost:{FLASK_PORT}/session")
    print("=" * 50 + "\n")
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            threaded=True,
        )
    finally:
        camera.release()
        if face_detector:
            face_detector.close()
        logger.info("SleepGuard server shut down.")
