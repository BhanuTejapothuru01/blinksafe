"""
Unit tests for BlinkSafe Low-End Mobile / 2 GB RAM Performance Optimizations
and Emergency SOS System.
"""

import time
import pytest
from config.config import (
    get_scaled_consec_frames,
    LOW_END_MODE,
    PROCESSING_FPS,
    FRAME_WIDTH,
    FRAME_HEIGHT,
)
from utils.sos_manager import SOSManager


def test_scaled_consec_frames_calculation():
    """Verify that get_scaled_consec_frames accurately scales frame thresholds."""
    # 15 frames @ 30 FPS = 0.5s -> at 10 FPS should be 5 frames
    assert get_scaled_consec_frames(15, base_fps=30.0, current_fps=10.0) == 5
    # 15 frames @ 30 FPS = 0.5s -> at 6 FPS should be 3 frames
    assert get_scaled_consec_frames(15, base_fps=30.0, current_fps=6.0) == 3
    # 10 frames @ 30 FPS = 0.33s -> at 15 FPS should be 5 frames
    assert get_scaled_consec_frames(10, base_fps=30.0, current_fps=15.0) == 5
    # Lower bound safety fallback
    assert get_scaled_consec_frames(1, base_fps=30.0, current_fps=1.0) >= 1


def test_sos_manager_lifecycle():
    """Test SOSManager trigger, countdown, status inspection, and cancellation."""
    sos = SOSManager(countdown_seconds=60)
    assert not sos.get_status()['active']

    # Trigger 1-second test countdown
    assert sos.trigger(duration_seconds=1)
    status = sos.get_status()
    assert status['active']
    assert status['remaining_seconds'] <= 1

    # Cancel SOS
    assert sos.cancel()
    status_after_cancel = sos.get_status()
    assert not status_after_cancel['active']
    assert status_after_cancel['remaining_seconds'] == 0


def test_mobile_performance_config_defaults():
    """Verify mobile performance configuration parameters."""
    assert isinstance(LOW_END_MODE, bool)
    assert isinstance(PROCESSING_FPS, int)
    assert PROCESSING_FPS > 0
    assert FRAME_WIDTH in (480, 640)
    assert FRAME_HEIGHT in (360, 480)
