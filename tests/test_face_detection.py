"""
Tests for Face Landmark Detection Engine (Phase 2).
"""

import os
import pytest
import numpy as np
from detection.face_detector import FaceDetector
from config.config import MODEL_PATH


def test_face_detector_init_valid():
    """Test initializing FaceDetector with valid model path."""
    detector = FaceDetector(model_path=MODEL_PATH)
    assert detector is not None
    detector.close()


def test_face_detector_init_invalid_path():
    """Test initializing FaceDetector with non-existent model path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        FaceDetector(model_path="non_existent_model.task")


def test_face_detector_empty_frame():
    """Test detect() with empty/invalid frame inputs returns None."""
    detector = FaceDetector(model_path=MODEL_PATH)
    try:
        assert detector.detect(None) is None
        empty_frame = np.array([], dtype=np.uint8)
        assert detector.detect(empty_frame) is None
    finally:
        detector.close()


def test_face_detector_black_frame():
    """Test detect() on a blank black image (no face detected)."""
    detector = FaceDetector(model_path=MODEL_PATH)
    try:
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.detect(black_frame)
        assert result is None
    finally:
        detector.close()


def test_draw_landmarks_handles_none():
    """Test draw_landmarks handles None detection_result gracefully."""
    detector = FaceDetector(model_path=MODEL_PATH)
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        annotated = detector.draw_landmarks(frame, None)
        assert np.array_equal(frame, annotated)
    finally:
        detector.close()
