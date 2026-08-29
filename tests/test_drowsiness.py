"""
Tests for Drowsiness Fusion Engine & Alarm Manager (Phase 6).
"""

import os
import time
import pytest
from detection.drowsiness_engine import DrowsinessEngine
from alerts.alarm import AlarmManager
from config.config import ALARM_SOUND_PATH


def test_drowsiness_engine_alert():
    """Test engine defaults to ALERT when all indicators are clear."""
    engine = DrowsinessEngine(hysteresis_frames=3)
    eye_state = {'ear': 0.35, 'closed': False}
    mouth_state = {'mar': 0.15, 'yawning': False}
    head_state = {'pitch': 0.0, 'yaw': 0.0, 'nodding': False}

    res = engine.update(eye_state, mouth_state, head_state)
    assert res['state'] == 'ALERT'
    assert res['confidence'] == 0.0


def test_drowsiness_engine_drowsy_transition():
    """Test engine transitions to DROWSY after sustained closed eyes."""
    engine = DrowsinessEngine(hysteresis_frames=3)
    eye_closed = {'ear': 0.10, 'closed': True}
    mouth_clear = {'mar': 0.15, 'yawning': False}
    head_clear = {'pitch': 0.0, 'yaw': 0.0, 'nodding': False}

    # Frame 1 & 2: pending count increases, state is still ALERT
    res1 = engine.update(eye_closed, mouth_clear, head_clear)
    res2 = engine.update(eye_closed, mouth_clear, head_clear)
    assert res1['state'] == 'ALERT'
    assert res2['state'] == 'ALERT'

    # Frame 3: hysteresis reached → DROWSY
    res3 = engine.update(eye_closed, mouth_clear, head_clear)
    assert res3['state'] == 'DROWSY'


def test_drowsiness_engine_danger_transition():
    """Test engine transitions to DANGER when both eyes closed and head nodding."""
    engine = DrowsinessEngine(hysteresis_frames=3)
    eye_closed = {'ear': 0.10, 'closed': True}
    mouth_clear = {'mar': 0.15, 'yawning': False}
    head_nodding = {'pitch': -25.0, 'yaw': 0.0, 'nodding': True}

    for _ in range(3):
        res = engine.update(eye_closed, mouth_clear, head_nodding)

    assert res['state'] == 'DANGER'
    assert res['confidence'] >= 0.75


def test_alarm_manager_cooldown(tmp_path):
    """Test AlarmManager plays sound once and enforces cooldown."""
    dummy_wav = tmp_path / "test_alarm.wav"
    dummy_wav.write_bytes(b"RIFF....WAVEfmt ....data....")

    alarm = AlarmManager(sound_path=str(dummy_wav), cooldown_seconds=5.0)

    # First trigger succeeds
    assert alarm.trigger() is True

    # Immediate second trigger is blocked by cooldown
    assert alarm.trigger() is False

    # Reset allows trigger again
    alarm.reset()
    assert alarm.trigger() is True
