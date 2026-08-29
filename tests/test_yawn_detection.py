"""
Tests for Yawn / Mouth Detection Module (Phase 4).
"""

import pytest
from utils.calculations import calculate_mar
from detection.mouth_detector import MouthDetector, MOUTH_INDICES


def create_dummy_mouth_points(height=5.0, width=50.0):
    """
    Generate 8 mouth points:
    [p1, p2, p3, p4, p5, p6, p7, p8]
    Corners: p1=(-w/2, 0), p5=(w/2, 0)
    Top inner: p2=(-w/4, h/2), p3=(0, h/2), p4=(w/4, h/2)
    Bottom inner: p8=(-w/4, -h/2), p7=(0, -h/2), p6=(w/4, -h/2)
    """
    half_w = width / 2.0
    quarter_w = width / 4.0
    half_h = height / 2.0

    return [
        (-half_w, 0.0),        # p1 (left corner)
        (-quarter_w, half_h),   # p2 (top left)
        (0.0, half_h),         # p3 (top center)
        (quarter_w, half_h),    # p4 (top right)
        (half_w, 0.0),         # p5 (right corner)
        (quarter_w, -half_h),   # p6 (bottom right)
        (0.0, -half_h),        # p7 (bottom center)
        (-quarter_w, -half_h),  # p8 (bottom left)
    ]


def generate_full_face_landmarks_mouth(height=5.0, width=50.0):
    """Generate 478 face landmarks with specified mouth open height."""
    landmarks = [(0.0, 0.0, 0.0)] * 478
    mouth_pts = create_dummy_mouth_points(height=height, width=width)

    for idx, pt in zip(MOUTH_INDICES, mouth_pts):
        landmarks[idx] = (pt[0], pt[1], 0.0)

    return landmarks


def test_calculate_mar_closed_vs_yawn():
    """Test calculate_mar on closed mouth vs wide open yawn."""
    closed_pts = create_dummy_mouth_points(height=5.0, width=50.0)
    yawn_pts = create_dummy_mouth_points(height=55.0, width=50.0)

    closed_mar = calculate_mar(closed_pts)
    yawn_mar = calculate_mar(yawn_pts)

    assert closed_mar < 0.3
    assert yawn_mar > 0.8


def test_mouth_detector_normal():
    """Test MouthDetector with normal mouth (no yawn)."""
    detector = MouthDetector(mar_threshold=0.75, consec_frames=10)
    landmarks = generate_full_face_landmarks_mouth(height=5.0, width=50.0)

    for _ in range(15):
        res = detector.update(landmarks)

    assert res['yawning'] is False
    assert res['consec_frames'] == 0
    assert res['mar'] < 0.75


def test_mouth_detector_yawn_trigger():
    """Test MouthDetector triggers yawning=True after consec_frames of wide open mouth."""
    detector = MouthDetector(mar_threshold=0.75, consec_frames=5)
    yawn_landmarks = generate_full_face_landmarks_mouth(height=55.0, width=50.0)

    for i in range(1, 5):
        res = detector.update(yawn_landmarks)
        assert res['consec_frames'] == i
        assert res['yawning'] is False

    res = detector.update(yawn_landmarks)
    assert res['consec_frames'] == 5
    assert res['yawning'] is True


def test_mouth_detector_reset():
    """Test reset clears yawn frame counter."""
    detector = MouthDetector(mar_threshold=0.75, consec_frames=5)
    yawn_landmarks = generate_full_face_landmarks_mouth(height=55.0, width=50.0)

    for _ in range(5):
        detector.update(yawn_landmarks)

    assert detector.yawn_frame_count == 5
    detector.reset()
    assert detector.yawn_frame_count == 0
