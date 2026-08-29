"""
BlinkSafe — Driver Registry Manager

Coordinates driver registration, multi-sample face embedding extraction,
FAISS vector indexing, and SQLite database persistence with diagnostic logging.
"""

from datetime import datetime
import numpy as np

from database.database import DatabaseManager
from recognition.face_embedding import FaceEmbeddingExtractor
from recognition.faiss_manager import FAISSManager
from utils.logger import get_logger

logger = get_logger(__name__)


class DriverRegistry:
    """Manages driver profiles, multi-sample face registration, and FAISS indexing."""

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        embedding_extractor: FaceEmbeddingExtractor | None = None,
        faiss_manager: FAISSManager | None = None,
        face_detector=None,
    ):
        self.db = db_manager or DatabaseManager()
        self.extractor = embedding_extractor or FaceEmbeddingExtractor()
        self.faiss_manager = faiss_manager or FAISSManager()
        self.face_detector = face_detector

    def register_driver(
        self,
        name: str,
        phone: str,
        frames_or_crops: list[np.ndarray],
        bboxes: list[tuple | None] | None = None,
    ) -> dict:
        """
        Register a new driver with name, phone, and multi-frame face samples (e.g. 20-30 samples).

        Parameters:
            name: Driver's full name.
            phone: Driver's phone number.
            frames_or_crops: List of BGR numpy images representing face samples.
            bboxes: Optional list of (x, y, w, h) bounding boxes matching frames.

        Returns:
            {
                'status': 'success' | 'error',
                'driver_id': int | None,
                'name': str,
                'phone': str,
                'embeddings_added': int,
                'message': str,
            }
        """
        name = name.strip() if name else ""
        phone = phone.strip() if phone else ""

        if not name:
            return {'status': 'error', 'message': 'Driver name is required.'}
        if not phone:
            return {'status': 'error', 'message': 'Driver phone number is required.'}

        if not frames_or_crops:
            return {'status': 'error', 'message': 'At least one face sample image is required.'}

        # 1. Create driver record in SQLite database
        driver_id = self.db.create_driver(name, phone)
        if not driver_id:
            return {'status': 'error', 'message': 'Failed to create driver database record.'}

        bboxes = bboxes or [None] * len(frames_or_crops)
        added_count = 0

        # 2. Extract embedding and index into FAISS for each valid sample
        for i, img in enumerate(frames_or_crops):
            bbox = bboxes[i] if i < len(bboxes) else None
            landmarks = None

            # Detect face bbox and landmarks on raw frame if not provided
            if bbox is None and self.face_detector is not None:
                try:
                    detection = self.face_detector.detect(img)
                    if detection:
                        bbox = detection.get('bbox')
                        landmarks = detection.get('pixel_landmarks')
                except Exception as e:
                    logger.warning("Face detection failed during registration sample %d: %s", i + 1, e)

            emb = self.extractor.extract_embedding(img, bbox=bbox, landmarks=landmarks)

            if emb is not None and np.linalg.norm(emb) > 0.5:
                try:
                    faiss_id = self.faiss_manager.add_embedding(emb, driver_id)
                    self.db.log_face_embedding(driver_id, faiss_id)
                    added_count += 1

                    logger.info(
                        "[DRIVER REGISTRATION] Sample %d/%d - Face detected: YES | Quality: GOOD | Embedding generated: YES | Dimension: %d | FAISS ID: %d | Driver ID: %d | Registration: SUCCESS",
                        i + 1,
                        len(frames_or_crops),
                        len(emb),
                        faiss_id,
                        driver_id,
                    )
                except Exception as e:
                    logger.error("[DRIVER REGISTRATION] Sample %d/%d indexing failed: %s", i + 1, len(frames_or_crops), e)
            else:
                logger.warning("[DRIVER REGISTRATION] Sample %d/%d rejected (no usable face or poor quality).", i + 1, len(frames_or_crops))

        if added_count == 0:
            # Rollback empty driver record
            self.db.delete_driver(driver_id)
            return {
                'status': 'error',
                'message': 'No usable face detected in the provided samples. Please retry with clear face lighting.',
            }

        logger.info(
            "Registered driver '%s' (ID=%d, phone=%s) with %d indexed face embeddings in FAISS.",
            name,
            driver_id,
            phone,
            added_count,
        )

        return {
            'status': 'success',
            'driver_id': driver_id,
            'name': name,
            'phone': phone,
            'embeddings_added': added_count,
            'message': f"Driver '{name}' registered successfully with {added_count} indexed face embeddings.",
        }

    def register_driver_with_vectors(self, name: str, phone: str, embeddings: list[np.ndarray]) -> dict:
        """Register driver directly using pre-computed normalized 128D numpy embedding vectors."""
        name = name.strip() if name else ""
        phone = phone.strip() if phone else ""

        if not name or not phone:
            return {'status': 'error', 'message': 'Name and phone number are required.'}

        valid_embeddings = [self.extractor.normalize_embedding(e) for e in embeddings if e is not None]
        if not valid_embeddings:
            return {'status': 'error', 'message': 'No valid embedding vectors provided.'}

        driver_id = self.db.create_driver(name, phone)
        if not driver_id:
            return {'status': 'error', 'message': 'Failed to create driver record.'}

        added_count = 0
        for i, emb in enumerate(valid_embeddings):
            faiss_id = self.faiss_manager.add_embedding(emb, driver_id)
            self.db.log_face_embedding(driver_id, faiss_id)
            added_count += 1

            logger.info(
                "[DRIVER REGISTRATION] Vector %d/%d - FAISS ID: %d | Driver ID: %d | Registration: SUCCESS",
                i + 1,
                len(valid_embeddings),
                faiss_id,
                driver_id,
            )

        return {
            'status': 'success',
            'driver_id': driver_id,
            'name': name,
            'phone': phone,
            'embeddings_added': added_count,
            'message': f"Driver '{name}' registered successfully with {added_count} vectors.",
        }

    def get_driver(self, driver_id: int) -> dict | None:
        """Fetch driver profile by ID."""
        return self.db.get_driver_by_id(driver_id)

    def list_drivers(self) -> list[dict]:
        """List all active registered drivers."""
        return self.db.get_all_drivers()

    def delete_driver(self, driver_id: int) -> bool:
        """Delete driver profile from SQLite and reload FAISS index mapping."""
        success = self.db.delete_driver(driver_id)
        if success:
            self.faiss_manager.load_index()
            logger.info("Deleted driver ID %d and refreshed FAISS index.", driver_id)
        return success

    def reset_all(self) -> bool:
        """Reset and wipe all FAISS index vectors and driver embeddings for clean re-registration."""
        success = self.faiss_manager.reset_index()
        logger.info("Wiped clean all FAISS index vectors for fresh driver registration.")
        return success
