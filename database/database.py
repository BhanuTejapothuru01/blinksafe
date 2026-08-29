"""
SleepGuard — Database Manager

SQLite database connection, schema initialization, safe migrations, and CRUD methods
for drivers, face embeddings, monitoring sessions, and events.
"""

import os
import sqlite3
from datetime import datetime
from config.config import DB_PATH
from database.models import SessionModel, EventModel, DriverModel, FaceEmbeddingModel
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """SQLite wrapper managing persistence of drivers, embeddings, sessions, and events."""

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
        """Create tables if they don't exist and perform safe migrations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL DEFAULT 0.0,
                    drowsy_count INTEGER DEFAULT 0,
                    danger_count INTEGER DEFAULT 0,
                    yawn_count INTEGER DEFAULT 0,
                    blink_count INTEGER DEFAULT 0,
                    avg_ear REAL DEFAULT 0.0,
                    avg_mar REAL DEFAULT 0.0,
                    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL
                );
            """)

            # Auto-migration: check if driver_id column exists in sessions table
            cursor.execute("PRAGMA table_info(sessions);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'driver_id' not in columns:
                cursor.execute("ALTER TABLE sessions ADD COLUMN driver_id INTEGER;")
                logger.info("Migrated sessions table: added driver_id column.")

            # 2. Drivers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER DEFAULT 1
                );
            """)

            # 3. Driver Face Embeddings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS driver_face_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER NOT NULL,
                    faiss_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER NOT NULL,
                    faiss_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
                );
            """)

            # 4. Events table
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
            logger.info("Database schema initialized/migrated at %s", self.db_path)

    # ── Driver CRUD ──────────────────────────────────────────────────────────
    def create_driver(self, name: str, phone: str) -> int:
        """Insert a new driver record and return driver_id."""
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO drivers (name, phone, created_at, updated_at, active) VALUES (?, ?, ?, ?, 1)",
                (name, phone, now_iso, now_iso),
            )
            conn.commit()
            driver_id = cursor.lastrowid
            logger.info("Created driver record ID: %d (Name: %s)", driver_id, name)
            return driver_id

    def get_all_drivers(self) -> list[dict]:
        """Fetch list of all active registered drivers."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drivers WHERE active = 1 ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_driver_by_id(self, driver_id: int) -> dict | None:
        """Fetch driver profile by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drivers WHERE id = ? AND active = 1", (driver_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_driver(self, driver_id: int) -> bool:
        """Soft delete driver profile and remove face embeddings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE drivers SET active = 0 WHERE id = ?", (driver_id,))
            cursor.execute("DELETE FROM driver_face_embeddings WHERE driver_id = ?", (driver_id,))
            cursor.execute("DELETE FROM face_embeddings WHERE driver_id = ?", (driver_id,))
            conn.commit()
            logger.info("Deactivated driver ID: %d", driver_id)
            return cursor.rowcount > 0

    def log_face_embedding(self, driver_id: int, faiss_id: int) -> int:
        """Insert face embedding mapping into SQLite."""
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO driver_face_embeddings (driver_id, faiss_id, created_at) VALUES (?, ?, ?)",
                (driver_id, faiss_id, now_iso),
            )
            cursor.execute(
                "INSERT INTO face_embeddings (driver_id, faiss_id, created_at) VALUES (?, ?, ?)",
                (driver_id, faiss_id, now_iso),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_active_embeddings(self) -> list[dict]:
        """Fetch all face embedding mapping records for active drivers."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fe.*, d.name as driver_name 
                FROM face_embeddings fe
                JOIN drivers d ON fe.driver_id = d.id
                WHERE d.active = 1
            """)
            return [dict(r) for r in cursor.fetchall()]

    # ── Session CRUD ─────────────────────────────────────────────────────────
    def start_session(self, driver_id: int | None = None) -> int:
        """Create a new session record (optionally bound to driver_id) and return its ID."""
        start_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (start_time, driver_id) VALUES (?, ?)",
                (start_iso, driver_id),
            )
            conn.commit()
            session_id = cursor.lastrowid
            logger.info("Started session ID: %d (driver_id: %s)", session_id, driver_id)
            return session_id

    def update_session_driver(self, session_id: int, driver_id: int) -> bool:
        """Update driver_id for an active session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET driver_id = ? WHERE id = ?", (driver_id, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def end_session(self, session_id: int, summary: dict | None = None) -> bool:
        """Update end_time and final statistics for a session."""
        if summary is None:
            summary = {}

        end_iso = datetime.now().isoformat()
        driver_id = summary.get('driver_id')

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
                    avg_mar = ?,
                    driver_id = COALESCE(?, driver_id)
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
                    driver_id,
                    session_id,
                ),
            )
            conn.commit()
            logger.info("Ended session ID: %d", session_id)
            return cursor.rowcount > 0

    def get_all_sessions(self, limit: int = 50) -> list[dict]:
        """Fetch list of sessions joined with driver details, ordered by start_time descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, d.name as driver_name, d.phone as driver_phone
                FROM sessions s
                LEFT JOIN drivers d ON s.driver_id = d.id
                ORDER BY s.id DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_session_by_id(self, session_id: int) -> dict | None:
        """Fetch a single session by ID along with driver info and logged events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, d.name as driver_name, d.phone as driver_phone
                FROM sessions s
                LEFT JOIN drivers d ON s.driver_id = d.id
                WHERE s.id = ?
                """,
                (session_id,),
            )
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
