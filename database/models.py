"""
SleepGuard — Database Data Models

Data classes representing monitoring sessions and events.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionModel:
    """Represents a single monitoring session."""
    id: int | None = None
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str | None = None
    duration_seconds: float = 0.0
    drowsy_count: int = 0
    danger_count: int = 0
    yawn_count: int = 0
    blink_count: int = 0
    avg_ear: float = 0.0
    avg_mar: float = 0.0


@dataclass
class EventModel:
    """Represents a discrete drowsiness alert or metric event during a session."""
    session_id: int
    event_type: str  # 'DROWSY', 'DANGER', 'YAWN', 'MICROSLEEP'
    id: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0
    ear: float | None = None
    mar: float | None = None
    pitch: float | None = None
    yaw: float | None = None
