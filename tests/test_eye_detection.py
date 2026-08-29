"""
Tests for Eye Closure Detection Module (Phase 3).
"""

import pytest
from utils.calculations import calculate_ear
from detection.eye_detector import EyeDetector, LEFT_EYE_INDICES, RIGHT_EYE_INDICES


def create_dummy_eye_points(height=10.0, width=30.0):
    """
    Generate 6 eye points [p1, p2, p3, p4, p5, p6]
    p1=(-width/2, 0), p4=(width/2, 0)
    p2=(-width/4, height/2), p3=(width/4, height/2)
    p6=(-width/4, -height/2), p5=(width/4, -height/2)
    """
    half_w = width / 2.0
    quarter_w = width / 4.0
    half_h = height / 2.0

    return [
        (-half_w, 0.0),       # p1 (left corner)
        (-quarter_w, half_h),  # p2 (top left)
        (quarter_w, half_h),   # p3 (top right)
        (half_w, 0.0),        # p4 (right corner)
        (quarter_w, -half_h),  # p5 (bottom right)
        (-quarter_w, -half_h), # p6 (bottom left)
    ]


def generate_full_face_landmarks(eye_height=10.0, eye_width=30.0):
    """Generate 478 face landmarks with specified eye open height."""
    landmarks = [(0.0, 0.0, 0.0)] * 478
    eye_pts = create_dummy_eye_points(height=eye_height, width=eye_width)

    for idx, pt in zip(LEFT_EYE_INDICES, eye_pts):
        landmarks[idx] = (pt[0], pt[1], 0.0)

    for idx, pt in zip(RIGHT_EYE_INDICES, eye_pts):
        landmarks[idx] = (pt[0], pt[1], 0.0)

    return landmarks


def test_calculate_ear_open_closed():
    """Test calculate_ear formula on open vs closed eye geometries."""
    open_eye = create_dummy_eye_points(height=10.0, width=30.0)
    closed_eye = create_dummy_eye_points(height=1.0, width=30.0)

    open_ear = calculate_ear(open_eye)
    closed_ear = calculate_ear(closed_eye)

    assert open_ear > 0.25
    assert closed_ear < 0.10


def test_eye_detector_open_eyes():
    """Test EyeDetector with open eye landmarks."""
    detector = EyeDetector(ear_threshold=0.21, consec_frames=15)
    landmarks = generate_full_face_landmarks(eye_height=10.0, eye_width=30.0)

    for _ in range(20):
        res = detector.update(landmarks)

    assert res['closed'] is False
    assert res['consec_frames'] == 0
    assert res['ear'] > 0.21


def test_eye_detector_sustained_closure():
    """Test EyeDetector triggers closed=True after consec_frames of closed eyes."""
    detector = EyeDetector(ear_threshold=0.21, consec_frames=5)
    closed_landmarks = generate_full_face_landmarks(eye_height=1.0, eye_width=30.0)

    # First 4 frames: closed count increases, closed is False
    for i in range(1, 5):
        res = detector.update(closed_landmarks)
        assert res['consec_frames'] == i
        assert res['closed'] is False

    # 5th frame: triggers closed=True
    res = detector.update(closed_landmarks)
    assert res['consec_frames'] == 5
    assert res['closed'] is True


def test_eye_detector_reset():
    """Test reset clears closed frame counter."""
    detector = EyeDetector(ear_threshold=0.21, consec_frames=5)
    closed_landmarks = generate_full_face_landmarks(eye_height=1.0, eye_width=30.0)

    for _ in range(5):
        detector.update(closed_landmarks)

    assert detector.closed_frame_count == 5
    detector.reset()
    assert detector.closed_frame_count == 0
