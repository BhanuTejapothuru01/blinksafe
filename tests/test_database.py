"""
Tests for Persistence & Database Layer (Phase 7).
"""

import pytest
from database.database import DatabaseManager


@pytest.fixture
def db(tmp_path):
    """Fixture initializing temporary SQLite database."""
    db_file = tmp_path / "test_sleepguard.db"
    return DatabaseManager(db_path=str(db_file))


def test_db_init_and_tables(db):
    """Test schema initialization creates tables."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    assert 'sessions' in tables
    assert 'events' in tables


def test_session_lifecycle(db):
    """Test starting, ending, and fetching a session."""
    session_id = db.start_session()
    assert session_id is not None and session_id > 0

    summary = {
        'duration_seconds': 120.5,
        'drowsy_count': 3,
        'danger_count': 1,
        'yawn_count': 2,
        'blink_count': 45,
        'avg_ear': 0.28,
        'avg_mar': 0.18,
    }
    success = db.end_session(session_id, summary)
    assert success is True

    fetched = db.get_session_by_id(session_id)
    assert fetched is not None
    assert fetched['id'] == session_id
    assert fetched['drowsy_count'] == 3
    assert fetched['danger_count'] == 1
    assert fetched['duration_seconds'] == 120.5


def test_log_and_fetch_events(db):
    """Test logging events for a session and fetching them."""
    session_id = db.start_session()

    event_id1 = db.log_event(session_id, event_type='YAWN', confidence=0.8, mar=0.82)
    event_id2 = db.log_event(session_id, event_type='DANGER', confidence=0.9, ear=0.08, pitch=-20.0)

    assert event_id1 > 0
    assert event_id2 > 0

    session_data = db.get_session_by_id(session_id)
    events = session_data['events']
    assert len(events) == 2
    assert events[0]['event_type'] == 'YAWN'
    assert events[1]['event_type'] == 'DANGER'
