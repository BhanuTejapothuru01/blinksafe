"""
SleepGuard / BlinkSafe — Main Flask Application

Routes:
  /                  → Dashboard (index.html)
  /session           → Live monitoring page (session.html)
  /report/<id>       → Session report page (report.html)
  /video_feed        → MJPEG stream with drowsiness & face recognition overlays
  /api/status        → Live metrics, drowsiness & driver identity state
  /api/drivers       → Driver management (list, register, delete)
  /api/driver/current → Current identified driver status
  /api/session/start → Start monitoring session (bound to identified driver)
  /api/session/stop  → Stop active session
  /api/report/<id>   → Session report data endpoint
"""

import time
import base64
from datetime import datetime
import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request

from camera.camera_manager import CameraManager
from config.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, DRAW_LANDMARKS, RECOGNITION_FRAME_INTERVAL
from utils.logger import get_logger

from detection.face_detector import FaceDetector
from detection.eye_detector import EyeDetector
from detection.mouth_detector import MouthDetector
from detection.head_pose import HeadPoseEstimator
from detection.drowsiness_engine import DrowsinessEngine
from alerts.alarm import AlarmManager
from database.database import DatabaseManager
from reports.report_generator import ReportGenerator

from recognition.face_embedding import FaceEmbeddingExtractor
from recognition.faiss_manager import FAISSManager
from recognition.face_recognizer import FaceRecognizer
from recognition.driver_registry import DriverRegistry

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

# ── Driver Recognition & FAISS Vector Search ─────────────────────────────
embedding_extractor = FaceEmbeddingExtractor()
faiss_manager = FAISSManager()
face_recognizer = FaceRecognizer(
    embedding_extractor=embedding_extractor,
    faiss_manager=faiss_manager,
)
driver_registry = DriverRegistry(
    db_manager=db_manager,
    embedding_extractor=embedding_extractor,
    faiss_manager=faiss_manager,
    face_detector=face_detector,
)

# ── Global Live State ────────────────────────────────────────────────────
frame_counter = 0

session_state = {
    'active': False,
    'session_id': None,
    'driver_id': None,
    'driver_name': 'Unknown Driver',
    'driver_phone': 'N/A',
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
    # Driver identity metrics
    'driver_status': 'VERIFYING',
    'driver_id': None,
    'driver_name': 'Unknown Driver',
    'driver_phone': 'N/A',
    'similarity_score': 0.0,
}


def process_frame(frame: np.ndarray) -> np.ndarray:
    """Run real-time drowsiness pipeline on every frame + face recognition every N frames."""
    global latest_frame_metrics, frame_counter

    if frame is None or face_detector is None:
        return frame

    frame_counter += 1
    h, w = frame.shape[:2]
    detection = face_detector.detect(frame)

    if detection and detection.get('landmarks'):
        landmarks = detection['landmarks']
        pixel_landmarks = detection.get('pixel_landmarks', [])
        bbox = detection.get('bbox')

        # 1. ALWAYS RUN REAL-TIME DROWSINESS PIPELINE ON EVERY FRAME
        eye_res = eye_detector.update(landmarks)
        mouth_res = mouth_detector.update(landmarks)
        head_res = head_pose_estimator.update(landmarks, frame_shape=(h, w))
        fused = drowsiness_engine.update(eye_res, mouth_res, head_res)

        # 2. RUN DRIVER FACE RECOGNITION AT CONFIGURED FRAME INTERVAL
        if frame_counter % RECOGNITION_FRAME_INTERVAL == 0:
            rec_res = face_recognizer.update(
                frame,
                bbox=bbox,
                landmarks=pixel_landmarks,
                num_faces=1,
            )
            
            rec_status = rec_res['status']
            rec_driver_id = rec_res['driver_id']
            score = rec_res['similarity_score']

            top2_sc = rec_res.get('top2_score', 0.0)
            margin_sc = rec_res.get('margin', 0.0)

            if rec_status == FaceRecognizer.STATUS_CONFIRMED and rec_driver_id:
                driver_info = driver_registry.get_driver(rec_driver_id)
                if driver_info:
                    d_name = driver_info['name']
                    d_phone = driver_info['phone']
                else:
                    d_name = f"Driver #{rec_driver_id}"
                    d_phone = "N/A"

                latest_frame_metrics.update({
                    'driver_status': 'CONFIRMED',
                    'driver_id': rec_driver_id,
                    'driver_name': d_name,
                    'driver_phone': d_phone,
                    'similarity_score': score,
                    'top2_score': top2_sc,
                    'margin': margin_sc,
                })

                # Bind confirmed driver to session state & DB if active session
                session_state['driver_id'] = rec_driver_id
                session_state['driver_name'] = d_name
                session_state['driver_phone'] = d_phone
                if session_state['active'] and session_state['session_id']:
                    db_manager.update_session_driver(session_state['session_id'], rec_driver_id)

            elif rec_status == FaceRecognizer.STATUS_UNKNOWN:
                latest_frame_metrics.update({
                    'driver_status': 'UNKNOWN_DRIVER',
                    'driver_id': None,
                    'driver_name': 'Unknown Driver',
                    'driver_phone': 'N/A',
                    'similarity_score': score,
                    'top2_score': top2_sc,
                    'margin': margin_sc,
                })
                if not session_state['active']:
                    session_state['driver_name'] = 'Unknown Driver'

            elif rec_status == FaceRecognizer.STATUS_MULTIPLE_FACES:
                latest_frame_metrics.update({
                    'driver_status': 'MULTIPLE_FACES',
                    'similarity_score': 0.0,
                    'top2_score': 0.0,
                    'margin': 0.0,
                })

            elif rec_status == FaceRecognizer.STATUS_VERIFYING:
                latest_frame_metrics.update({
                    'driver_status': 'VERIFYING',
                    'similarity_score': score,
                    'top2_score': top2_sc,
                    'margin': margin_sc,
                })

        # Update latest frame drowsiness metrics
        latest_frame_metrics.update({
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
        })

        # Trigger audio alarm on DANGER state
        if fused['state'] == DrowsinessEngine.STATE_DANGER:
            alarm_manager.trigger()

        # Session tracking & DB event logging
        if session_state['active'] and session_state['session_id']:
            sess_id = session_state['session_id']

            session_state['ear_samples'].append(eye_res['ear'])
            session_state['mar_samples'].append(mouth_res['mar'])
            if len(session_state['ear_samples']) > 10000:
                session_state['ear_samples'] = session_state['ear_samples'][-5000:]
            if len(session_state['mar_samples']) > 10000:
                session_state['mar_samples'] = session_state['mar_samples'][-5000:]

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

        # Draw landmarks & bounding box
        if DRAW_LANDMARKS:
            frame = face_detector.draw_landmarks(frame, detection, draw_bbox=True)

        # 3. DRAW UI OVERLAY (Top State Banner + Bottom Driver Badge)
        state = fused['state']
        color = (0, 220, 0) if state == 'ALERT' else ((0, 165, 255) if state == 'DROWSY' else (0, 0, 255))
        
        # Top banner
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

        # Bottom driver badge
        d_status = latest_frame_metrics['driver_status']
        d_name = latest_frame_metrics['driver_name']
        if d_status == 'CONFIRMED':
            badge_text = f"DRIVER: {d_name}"
            badge_color = (0, 220, 0)  # Green
        elif d_status == 'VERIFYING':
            badge_text = "DRIVER: VERIFYING..."
            badge_color = (0, 165, 255)  # Orange
        elif d_status == 'MULTIPLE_FACES':
            badge_text = "DRIVER: MULTIPLE FACES"
            badge_color = (180, 0, 180)  # Purple
        else:
            badge_text = "DRIVER: UNKNOWN"
            badge_color = (0, 0, 220)  # Red

        cv2.rectangle(frame, (0, h - 35), (w, h), (15, 23, 42), -1)
        cv2.putText(frame, badge_text, (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, badge_color, 2, cv2.LINE_AA)

    else:
        # No face detected
        latest_frame_metrics['state'] = 'NO FACE'
        latest_frame_metrics['driver_status'] = 'NO_FACE'
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


# ── Driver Management APIs ───────────────────────────────────────────────
@app.route('/api/drivers', methods=['GET'])
def api_get_drivers():
    drivers = driver_registry.list_drivers()
    return jsonify({'drivers': drivers})


@app.route('/api/drivers/<int:driver_id>', methods=['GET'])
def api_get_driver(driver_id):
    driver = driver_registry.get_driver(driver_id)
    if not driver:
        return jsonify({'error': 'Driver not found'}), 404
    return jsonify(driver)


@app.route('/api/drivers/register', methods=['POST'])
def api_register_driver():
    data = request.get_json(silent=True) or request.form
    name = data.get('name')
    phone = data.get('phone')
    samples_base64 = data.get('samples', [])

    if not name or not phone:
        return jsonify({'status': 'error', 'message': 'Name and phone number are required.'}), 400

    # Decode base64 image samples if provided by frontend camera capture
    bgr_samples = []
    if isinstance(samples_base64, list):
        for s_b64 in samples_base64:
            try:
                if ',' in s_b64:
                    s_b64 = s_b64.split(',', 1)[1]
                img_bytes = base64.b64decode(s_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is not None:
                    bgr_samples.append(img)
            except Exception as e:
                logger.warning("Failed to decode base64 face sample: %s", e)

    # If no base64 images sent, capture a multi-sample burst (20 frames) from live camera feed
    if not bgr_samples:
        from config.config import REGISTRATION_SAMPLE_COUNT
        for _ in range(REGISTRATION_SAMPLE_COUNT):
            ret, current_frame = camera.read_frame()
            if ret and current_frame is not None:
                bgr_samples.append(current_frame.copy())
            time.sleep(0.08)

    if not bgr_samples:
        return jsonify({'status': 'error', 'message': 'No camera frame or face samples available.'}), 400

    result = driver_registry.register_driver(name=name, phone=phone, frames_or_crops=bgr_samples)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code


@app.route('/api/drivers/recognize', methods=['POST'])
def api_recognize_driver():
    data = request.get_json(silent=True) or {}
    sample_b64 = data.get('image')
    
    frame = None
    if sample_b64:
        try:
            if ',' in sample_b64:
                sample_b64 = sample_b64.split(',', 1)[1]
            img_bytes = base64.b64decode(sample_b64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception:
            frame = None

    if frame is None:
        ret, frame = camera.read_frame()

    if frame is None:
        return jsonify({'status': 'error', 'message': 'No camera frame available.'}), 400

    detection = face_detector.detect(frame) if face_detector else None
    bbox = detection.get('bbox') if detection else None
    landmarks = detection.get('pixel_landmarks') if detection else None

    res = face_recognizer.update(frame, bbox=bbox, landmarks=landmarks)
    driver_info = driver_registry.get_driver(res['driver_id']) if res['driver_id'] else None

    return jsonify({
        'status': res['status'],
        'driver_id': res['driver_id'],
        'driver_name': driver_info['name'] if driver_info else 'Unknown Driver',
        'driver_phone': driver_info['phone'] if driver_info else 'N/A',
        'similarity_score': res['similarity_score'],
        'confidence': res['confidence'],
    })


@app.route('/api/drivers/<int:driver_id>', methods=['DELETE'])
def api_delete_driver(driver_id):
    success = driver_registry.delete_driver(driver_id)
    if success:
        return jsonify({'status': 'success', 'message': f'Driver {driver_id} deleted.'})
    return jsonify({'status': 'error', 'message': 'Driver not found or delete failed.'}), 404


@app.route('/api/drivers/reset', methods=['POST'])
def api_reset_drivers():
    """Wipe clean the FAISS vector index and memory mappings for fresh re-registration."""
    success = driver_registry.reset_all()
    face_recognizer.reset()
    return jsonify({
        'status': 'success' if success else 'error',
        'message': 'FAISS vector index wiped clean for fresh re-registration.'
    })


@app.route('/api/test-alarm', methods=['POST'])
def api_test_alarm():
    """Directly execute alarm sound playback independent of face detection."""
    played = alarm_manager.trigger(force=True)
    return jsonify({
        'status': 'success' if played else 'error',
        'sound_path': ALARM_SOUND_PATH,
        'exists': os.path.exists(ALARM_SOUND_PATH),
        'platform': sys.platform,
        'played': played,
        'message': 'Executed afplay alarm sound trigger.'
    })


@app.route('/api/diagnostic-mode', methods=['GET'])
def api_diagnostic_mode():
    """Returns complete development-mode diagnostic state (Part C)."""
    return jsonify({
        'driver_name': latest_frame_metrics.get('driver_name', 'Unknown'),
        'driver_status': latest_frame_metrics.get('driver_status', 'VERIFYING'),
        'top1_similarity_score': latest_frame_metrics.get('similarity_score', 0.0),
        'top2_similarity_score': latest_frame_metrics.get('top2_score', 0.0),
        'match_margin': latest_frame_metrics.get('margin', 0.0),
        'drowsiness_state': latest_frame_metrics.get('state', 'ALERT'),
        'drowsiness_confidence': latest_frame_metrics.get('confidence', 0.0),
        'ear': latest_frame_metrics.get('ear', 0.0),
        'mar': latest_frame_metrics.get('mar', 0.0),
        'pitch': latest_frame_metrics.get('pitch', 0.0),
        'yaw': latest_frame_metrics.get('yaw', 0.0),
        'head_nodding': latest_frame_metrics.get('nodding', False),
        'eye_closed': latest_frame_metrics.get('eye_closed', False),
        'yawning': latest_frame_metrics.get('yawning', False),
        'sustained_closed_frames': drowsiness_engine.sustained_closed_frames if drowsiness_engine else 0,
        'alarm_sound_exists': os.path.exists(ALARM_SOUND_PATH),
        'alarm_sound_path': ALARM_SOUND_PATH,
    })


@app.route('/api/driver/current', methods=['GET'])
def api_current_driver():
    return jsonify({
        'status': latest_frame_metrics['driver_status'],
        'driver_id': latest_frame_metrics['driver_id'],
        'name': latest_frame_metrics['driver_name'],
        'phone': latest_frame_metrics['driver_phone'],
        'similarity_score': latest_frame_metrics['similarity_score'],
        'top2_score': latest_frame_metrics.get('top2_score', 0.0),
        'margin': latest_frame_metrics.get('margin', 0.0),
    })


# ── Monitoring Session APIs ──────────────────────────────────────────────
@app.route('/api/session/start', methods=['POST'])
def api_start_session():
    if session_state['active']:
        return jsonify({'status': 'already_active', 'session_id': session_state['session_id']})

    active_driver_id = latest_frame_metrics['driver_id']
    session_id = db_manager.start_session(driver_id=active_driver_id)
    
    session_state['active'] = True
    session_state['session_id'] = session_id
    session_state['driver_id'] = active_driver_id
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
    face_recognizer.reset()

    return jsonify({'status': 'started', 'session_id': session_id, 'driver_id': active_driver_id})


@app.route('/api/session/stop', methods=['POST'])
def api_stop_session():
    if not session_state['active'] or not session_state['session_id']:
        return jsonify({'status': 'no_active_session'}), 400

    session_id = session_state['session_id']
    duration_sec = round(time.time() - (session_state['start_time'] or time.time()), 1)

    avg_ear = float(np.mean(session_state['ear_samples'])) if session_state['ear_samples'] else 0.0
    avg_mar = float(np.mean(session_state['mar_samples'])) if session_state['mar_samples'] else 0.0

    summary = {
        'driver_id': session_state['driver_id'],
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
