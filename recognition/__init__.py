"""
BlinkSafe — Face Recognition & Driver Identification Package

Exports face embedding extractor, FAISS vector index manager, temporal face recognizer,
and driver registry modules.
"""

from recognition.face_embedding import FaceEmbeddingExtractor
from recognition.faiss_manager import FAISSManager
from recognition.face_recognizer import FaceRecognizer
from recognition.driver_registry import DriverRegistry

__all__ = [
    'FaceEmbeddingExtractor',
    'FAISSManager',
    'FaceRecognizer',
    'DriverRegistry',
]
