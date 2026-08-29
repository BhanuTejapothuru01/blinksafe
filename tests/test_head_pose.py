"""
Tests for Head Pose Estimation Module (Phase 5).
"""

import pytest
import numpy as np
from detection.head_pose import HeadPoseEstimator, LANDMARK_INDICES


def generate_head_landmarks(pitch_offset_px=0.0):
    """
    Generate dummy 478 face landmarks in normalized coords (640x480).
    Neutral face:
    Nose: (320, 240)
    Chin: (320, 360)
    Left eye: (250, 200)
    Right eye: (390, 200)
    Left mouth: (275, 300)
    Right mouth: (365, 300)
    """
    w, h = 640.0, 480.0
    landmarks = [(0.5, 0.5, 0.0)] * 478

    pts = {
        1: (320.0, 240.0 + pitch_offset_px),   # Nose tip (moving down simulates nodding)
        152: (320.0, 360.0),                  # Chin
        33: (250.0, 200.0),                   # Left eye
        263: (390.0, 200.0),                  # Right eye
        61: (275.0, 300.0),                   # Left mouth
        291: (365.0, 300.0),                  # Right mouth
    }

    for idx, (px, py) in pts.items():
        landmarks[idx] = (px / w, py / h, 0.0)

    return landmarks


def test_head_pose_neutral():
    """Test HeadPoseEstimator on neutral face position."""
    estimator = HeadPoseEstimator(pitch_threshold=-15.0, consec_frames=5)
    landmarks = generate_head_landmarks(pitch_offset_px=0.0)

    res = estimator.update(landmarks, frame_shape=(480, 640))

    assert 'pitch' in res
    assert 'yaw' in res
    assert 'roll' in res
    assert res['nodding'] is False
    assert res['consec_frames'] == 0


def test_head_pose_nodding_trigger():
    """Test HeadPoseEstimator triggers nodding=True when head pitches down sustained."""
    estimator = HeadPoseEstimator(pitch_threshold=-5.0, consec_frames=3)
    nodding_landmarks = generate_head_landmarks(pitch_offset_px=50.0)

    for i in range(1, 3):
        res = estimator.update(nodding_landmarks, frame_shape=(480, 640))
        assert res['consec_frames'] == i
        assert res['nodding'] is False

    res = estimator.update(nodding_landmarks, frame_shape=(480, 640))
    assert res['consec_frames'] == 3
    assert res['nodding'] is True


def test_head_pose_reset():
    """Test reset clears nod frame counter."""
    estimator = HeadPoseEstimator(pitch_threshold=-5.0, consec_frames=3)
    nodding_landmarks = generate_head_landmarks(pitch_offset_px=50.0)

    for _ in range(3):
        estimator.update(nodding_landmarks, frame_shape=(480, 640))

    assert estimator.nod_frame_count == 3
    estimator.reset()
    assert estimator.nod_frame_count == 0
