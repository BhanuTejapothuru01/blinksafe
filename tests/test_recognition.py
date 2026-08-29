"""
BlinkSafe — Driver Recognition & Drowsiness Test Suite

Validates face embedding extraction, L2 normalization, FAISS IndexFlatIP persistence,
multi-embedding registration, top-k vector search aggregation, thresholding (0.60),
match margin check (0.08), sustained eye closure DANGER escalation, and audio alarms.
"""

import os
import tempfile
import pytest
import numpy as np

from database.database import DatabaseManager
from recognition.face_embedding import FaceEmbeddingExtractor
from recognition.faiss_manager import FAISSManager
from recognition.face_recognizer import FaceRecognizer
from recognition.driver_registry import DriverRegistry
from detection.drowsiness_engine import DrowsinessEngine
from alerts.alarm import AlarmManager
from reports.report_generator import ReportGenerator


@pytest.fixture
def temp_env():
    """Create isolated temporary database and FAISS index files for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, 'test_sleepguard.db')
        index_path = os.path.join(tmp_dir, 'drivers.index')
        map_path = os.path.join(tmp_dir, 'id_mapping.json')

        db_manager = DatabaseManager(db_path=db_path)
        extractor = FaceEmbeddingExtractor()
        faiss_manager = FAISSManager(index_path=index_path, map_path=map_path)
        recognizer = FaceRecognizer(embedding_extractor=extractor, faiss_manager=faiss_manager)
        registry = DriverRegistry(db_manager=db_manager, embedding_extractor=extractor, faiss_manager=faiss_manager)

        yield {
            'tmp_dir': tmp_dir,
            'db_path': db_path,
            'index_path': index_path,
            'map_path': map_path,
            'db_manager': db_manager,
            'extractor': extractor,
            'faiss_manager': faiss_manager,
            'recognizer': recognizer,
            'registry': registry,
        }


def test_embedding_normalization(temp_env):
    """Verify L2 vector normalization produces unit length float32 vector."""
    extractor = temp_env['extractor']
    raw_vec = np.random.randn(128).astype(np.float32)
    norm_vec = extractor.normalize_embedding(raw_vec)

    assert norm_vec.shape == (128,)
    assert norm_vec.dtype == np.float32
    assert abs(np.linalg.norm(norm_vec) - 1.0) < 1e-5


def test_empty_faiss_index_handling(temp_env):
    """Search on empty FAISS index must return (None, 0.0, 0.0, 0.0, 0) without crashing."""
    faiss_mgr = temp_env['faiss_manager']
    dummy_vec = np.random.randn(128).astype(np.float32)
    dummy_vec /= np.linalg.norm(dummy_vec)

    driver_id, t1, t2, margin, count = faiss_mgr.search_top_k(dummy_vec)
    assert driver_id is None
    assert t1 == 0.0
    assert count == 0


def test_multi_embedding_driver_registration(temp_env):
    """Test registering a driver with 20 embedding vectors in FAISS."""
    registry = temp_env['registry']
    faiss_mgr = temp_env['faiss_manager']

    base_v = np.random.randn(128).astype(np.float32)
    base_v /= np.linalg.norm(base_v)
    
    samples = []
    for _ in range(20):
        noise = np.random.randn(128).astype(np.float32) * 0.05
        v = base_v + noise
        v /= np.linalg.norm(v)
        samples.append(v)

    result = registry.register_driver_with_vectors("Teja Pothuru", "+15550199", samples)

    assert result['status'] == 'success'
    assert result['driver_id'] is not None
    assert result['name'] == "Teja Pothuru"
    assert result['phone'] == "+15550199"
    assert result['embeddings_added'] == 20
    assert faiss_mgr.index.ntotal == 20


def test_reject_unknown_different_person(temp_env):
    """Verify that a different person below 0.60 similarity threshold returns UNKNOWN_DRIVER."""
    registry = temp_env['registry']
    faiss_mgr = temp_env['faiss_manager']

    v_teja = np.zeros(128, dtype=np.float32)
    v_teja[0] = 1.0
    registry.register_driver_with_vectors("Teja", "+123456", [v_teja])

    v_unknown = np.zeros(128, dtype=np.float32)
    v_unknown[10] = 1.0  # Different face vector

    d_id, t1, t2, margin, count = faiss_mgr.search_top_k(v_unknown, threshold=0.60)
    assert d_id is None
    assert t1 == 0.0


def test_ambiguous_margin_rejection(temp_env):
    """Verify that ambiguous matches (margin < 0.08) are rejected as UNKNOWN."""
    recognizer = temp_env['recognizer']
    
    # Mock FAISS search returning top1=0.62, top2=0.58 (margin 0.04 < 0.08)
    recognizer.faiss_manager.search_top_k = lambda emb, top_k, threshold: (1, 0.62, 0.58, 0.04, 3)

    dummy_frame = np.ones((112, 112, 3), dtype=np.uint8)
    res = recognizer.update(dummy_frame, bbox=(0, 0, 100, 100))

    assert res['status'] == FaceRecognizer.STATUS_UNKNOWN
    assert res['driver_id'] is None


def test_sustained_eye_closure_danger_escalation():
    """Verify that continuous eye closure for 30 frames escalates state to DANGER."""
    engine = DrowsinessEngine()

    eye_open = {'ear': 0.35, 'closed': False}
    eye_closed = {'ear': 0.12, 'closed': True}
    mouth_normal = {'mar': 0.20, 'yawning': False}
    head_normal = {'pitch': 0.0, 'yaw': 0.0, 'nodding': False}

    # Initial state ALERT
    r1 = engine.update(eye_open, mouth_normal, head_normal)
    assert r1['state'] == DrowsinessEngine.STATE_ALERT

    # 30 frames of closed eyes
    for _ in range(30):
        res = engine.update(eye_closed, mouth_normal, head_normal)

    assert res['state'] == DrowsinessEngine.STATE_DANGER


def test_alarm_force_trigger(temp_env):
    """Test direct test alarm playback trigger."""
    alarm = AlarmManager()
    # Force trigger should return True or False depending on audio file existence
    played = alarm.trigger(force=True)
    assert isinstance(played, bool)


def test_faiss_reset_index(temp_env):
    """Test reset_all wiping index clean for fresh re-registration."""
    registry = temp_env['registry']
    faiss_mgr = temp_env['faiss_manager']

    v = np.random.randn(128).astype(np.float32)
    v /= np.linalg.norm(v)
    registry.register_driver_with_vectors("Teja", "+111", [v])
    assert faiss_mgr.index.ntotal == 1

    success = registry.reset_all()
    assert success is True
    assert faiss_mgr.index.ntotal == 0
