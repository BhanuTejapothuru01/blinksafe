"""
Tests for Report Generator (Phase 8).
"""

import pytest
from database.database import DatabaseManager
from reports.report_generator import ReportGenerator


@pytest.fixture
def db_session(tmp_path):
    """Fixture returning DB manager and populated test session ID."""
    db_file = tmp_path / "test_report.db"
    db = DatabaseManager(db_path=str(db_file))

    session_id = db.start_session()
    db.log_event(session_id, 'YAWN', confidence=0.6, mar=0.8)
    db.log_event(session_id, 'DROWSY', confidence=0.7, ear=0.15)
    db.log_event(session_id, 'DANGER', confidence=0.9, ear=0.08, pitch=-20.0)

    summary = {
        'duration_seconds': 185.0,
        'drowsy_count': 1,
        'danger_count': 1,
        'yawn_count': 1,
        'blink_count': 20,
        'avg_ear': 0.25,
        'avg_mar': 0.20,
    }
    db.end_session(session_id, summary)

    return db, session_id


def test_report_generator_success(db_session):
    """Test report generator produces valid report dict structure."""
    db, session_id = db_session
    generator = ReportGenerator(db_manager=db)

    report = generator.generate(session_id)

    assert report['session_id'] == session_id
    assert report['duration_str'] == "3m 5s"
    assert report['drowsy_count'] == 1
    assert report['danger_count'] == 1
    assert report['safety_score'] < 100
    assert report['risk_level'] == "HIGH RISK"
    assert len(report['timeline']['labels']) == 3
    assert len(report['timeline']['confidence']) == 3


def test_report_generator_invalid_id(tmp_path):
    """Test report generator handles non-existent session ID gracefully."""
    db_file = tmp_path / "test_report_empty.db"
    db = DatabaseManager(db_path=str(db_file))
    generator = ReportGenerator(db_manager=db)

    report = generator.generate(99999)
    assert 'error' in report
