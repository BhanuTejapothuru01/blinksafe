"""
SleepGuard — Database Manager

SQLite database connection, schema initialization, and CRUD methods for sessions and events.
"""

import os
import sqlite3
from datetime import datetime
from config.config import DB_PATH
from database.models import SessionModel, EventModel
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """SQLite wrapper managing persistence of monitoring sessions and detection events."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Return a SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL DEFAULT 0.0,
                    drowsy_count INTEGER DEFAULT 0,
                    danger_count INTEGER DEFAULT 0,
                    yawn_count INTEGER DEFAULT 0,
                    blink_count INTEGER DEFAULT 0,
                    avg_ear REAL DEFAULT 0.0,
                    avg_mar REAL DEFAULT 0.0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    ear REAL,
                    mar REAL,
                    pitch REAL,
                    yaw REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
            """)
            conn.commit()
            logger.info("Database schema initialized at %s", self.db_path)

    # ── Session CRUD ─────────────────────────────────────────────────────────
    def start_session(self) -> int:
        """Create a new session record and return its ID."""
        start_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (start_time) VALUES (?)",
                (start_iso,),
            )
            conn.commit()
            session_id = cursor.lastrowid
            logger.info("Started session ID: %d", session_id)
            return session_id

    def end_session(self, session_id: int, summary: dict | None = None) -> bool:
        """Update end_time and final statistics for a session."""
        if summary is None:
            summary = {}

        end_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions
                SET end_time = ?,
                    duration_seconds = ?,
                    drowsy_count = ?,
                    danger_count = ?,
                    yawn_count = ?,
                    blink_count = ?,
                    avg_ear = ?,
                    avg_mar = ?
                WHERE id = ?
                """,
                (
                    end_iso,
                    summary.get('duration_seconds', 0.0),
                    summary.get('drowsy_count', 0),
                    summary.get('danger_count', 0),
                    summary.get('yawn_count', 0),
                    summary.get('blink_count', 0),
                    summary.get('avg_ear', 0.0),
                    summary.get('avg_mar', 0.0),
                    session_id,
                ),
            )
            conn.commit()
            logger.info("Ended session ID: %d", session_id)
            return cursor.rowcount > 0

    def get_all_sessions(self, limit: int = 50) -> list[dict]:
        """Fetch list of sessions ordered by start_time descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_session_by_id(self, session_id: int) -> dict | None:
        """Fetch a single session by ID along with its logged events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                return None

            session_dict = dict(session_row)
            cursor.execute("SELECT * FROM events WHERE session_id = ? ORDER BY id ASC", (session_id,))
            events = [dict(r) for r in cursor.fetchall()]
            session_dict['events'] = events
            return session_dict

    # ── Event CRUD ───────────────────────────────────────────────────────────
    def log_event(
        self,
        session_id: int,
        event_type: str,
        confidence: float = 0.0,
        ear: float | None = None,
        mar: float | None = None,
        pitch: float | None = None,
        yaw: float | None = None,
    ) -> int:
        """Insert a detection event for a given session."""
        timestamp_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (session_id, timestamp, event_type, confidence, ear, mar, pitch, yaw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, timestamp_iso, event_type, confidence, ear, mar, pitch, yaw),
            )
            conn.commit()
            return cursor.lastrowid
