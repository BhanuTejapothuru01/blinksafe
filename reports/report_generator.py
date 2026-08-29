"""
SleepGuard — Report Generator

Aggregates database session metrics and event logs into visual data structures for reports.
"""

from datetime import datetime
from database.database import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Builds report data dict from DB session/event records for Chart.js visualization."""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db = db_manager or DatabaseManager()

    def generate(self, session_id: int) -> dict:
        """
        Return structured report data for a given session.
        """
        session_data = self.db.get_session_by_id(session_id)
        if not session_data:
            return {'error': 'Session not found'}

        events = session_data.get('events', [])
        duration_sec = session_data.get('duration_seconds', 0.0)

        # Format duration
        mins = int(duration_sec // 60)
        secs = int(duration_sec % 60)
        duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        # Build timeline series for Chart.js
        timestamps = []
        confidence_series = []
        ear_series = []
        mar_series = []
        event_markers = []

        for evt in events:
            # Parse ISO timestamp to HH:MM:SS
            ts_str = evt.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts_str)
                time_label = dt.strftime('%H:%M:%S')
            except (ValueError, TypeError):
                time_label = ts_str

            timestamps.append(time_label)
            confidence_series.append(evt.get('confidence', 0.0))
            ear_series.append(evt.get('ear'))
            mar_series.append(evt.get('mar'))

            if evt.get('event_type') in ('DROWSY', 'DANGER', 'YAWN'):
                event_markers.append({
                    'time': time_label,
                    'type': evt['event_type'],
                    'confidence': evt.get('confidence', 0.0),
                })

        # Calculate safety index (100 = perfect, lower = dangerous)
        drowsy_cnt = session_data.get('drowsy_count', 0)
        danger_cnt = session_data.get('danger_count', 0)
        yawn_cnt = session_data.get('yawn_count', 0)

        risk_penalty = (drowsy_cnt * 10) + (danger_cnt * 25) + (yawn_cnt * 5)
        safety_score = max(0, min(100, 100 - risk_penalty))

        # Generate recommendation
        if safety_score < 50 or danger_cnt > 0:
            recommendation = "🚨 High Drowsiness Risk: Take an immediate 20-minute rest break before driving."
            risk_level = "HIGH RISK"
        elif safety_score < 80 or drowsy_cnt > 2:
            recommendation = "⚠️ Moderate Fatigue: Consider pulling over for fresh air or caffeine."
            risk_level = "MODERATE RISK"
        else:
            recommendation = "✅ Optimal Alertness: Great job! Stay attentive and take regular breaks."
            risk_level = "LOW RISK"

        # Driver metadata formatting
        driver_name = session_data.get('driver_name') or "Unknown / Not recorded"
        driver_phone = session_data.get('driver_phone') or "N/A"
        driver_id = session_data.get('driver_id')

        return {
            'session_id': session_id,
            'driver_id': driver_id,
            'driver_name': driver_name,
            'driver_phone': driver_phone,
            'start_time': session_data.get('start_time'),
            'end_time': session_data.get('end_time'),
            'duration_str': duration_str,
            'duration_seconds': duration_sec,
            'drowsy_count': drowsy_cnt,
            'danger_count': danger_cnt,
            'yawn_count': yawn_cnt,
            'blink_count': session_data.get('blink_count', 0),
            'avg_ear': round(session_data.get('avg_ear', 0.0), 3),
            'avg_mar': round(session_data.get('avg_mar', 0.0), 3),
            'safety_score': safety_score,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'timeline': {
                'labels': timestamps,
                'confidence': confidence_series,
                'ear': ear_series,
                'mar': mar_series,
                'events': event_markers,
            },
        }
