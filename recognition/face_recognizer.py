"""
BlinkSafe — Real-Time Face Recognizer

Combines FaceEmbeddingExtractor and FAISSManager with same-person similarity thresholding (0.60),
second-best candidate margin verification (0.08), top-k vector aggregation, and temporal voting.
"""

from collections import deque
import numpy as np

from config.config import RECOGNITION_SIMILARITY_THRESHOLD, MIN_MATCH_MARGIN, RECOGNITION_REQUIRED_FRAMES, RECOGNITION_VOTE_RATIO, RECOGNITION_TOP_K
from recognition.face_embedding import FaceEmbeddingExtractor
from recognition.faiss_manager import FAISSManager
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceRecognizer:
    """High-level temporal face recognition and identity tracking engine."""

    STATUS_VERIFYING = 'VERIFYING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_UNKNOWN = 'UNKNOWN_DRIVER'
    STATUS_MULTIPLE_FACES = 'MULTIPLE_FACES'
    STATUS_NO_FACE = 'NO_FACE'

    def __init__(
        self,
        embedding_extractor: FaceEmbeddingExtractor | None = None,
        faiss_manager: FAISSManager | None = None,
        threshold: float = RECOGNITION_SIMILARITY_THRESHOLD,
        min_margin: float = MIN_MATCH_MARGIN,
        voting_window: int = RECOGNITION_REQUIRED_FRAMES,
        vote_ratio: float = RECOGNITION_VOTE_RATIO,
    ):
        self.extractor = embedding_extractor or FaceEmbeddingExtractor()
        self.faiss_manager = faiss_manager or FAISSManager()
        self.threshold = threshold
        self.min_margin = min_margin
        self.voting_window = max(1, voting_window)
        self.vote_ratio = vote_ratio

        # Sliding window buffer storing recent predictions: (driver_id, top1_score, top2_score, margin, status)
        self.voting_buffer = deque(maxlen=self.voting_window)
        
        self.current_driver_id = None
        self.current_status = self.STATUS_VERIFYING
        self.last_score = 0.0
        self.last_top2_score = 0.0
        self.last_margin = 0.0

    def update(
        self,
        frame: np.ndarray,
        bbox: tuple | None = None,
        landmarks: list | None = None,
        num_faces: int = 1,
    ) -> dict:
        """
        Process a frame and return current recognized driver identity and state.
        Enforces BOTH same-person similarity threshold (0.60) AND candidate match margin (0.08).

        Returns:
            {
                'status': 'CONFIRMED' | 'VERIFYING' | 'UNKNOWN_DRIVER' | 'MULTIPLE_FACES' | 'NO_FACE',
                'driver_id': int | None,
                'similarity_score': float,
                'top2_score': float,
                'margin': float,
                'confidence': float,
            }
        """
        if frame is None:
            return self._build_result(self.STATUS_NO_FACE, None, 0.0, 0.0, 0.0)

        if num_faces > 1:
            self.voting_buffer.append(('MULTIPLE', 0.0, 0.0, 0.0, self.STATUS_MULTIPLE_FACES))
            return self._aggregate_votes()

        if bbox is None and landmarks is None:
            return self._build_result(self.STATUS_NO_FACE, None, 0.0, 0.0, 0.0)

        # 1. Extract 128D normalized embedding vector (with facial affine alignment)
        embedding = self.extractor.extract_embedding(frame, bbox=bbox, landmarks=landmarks)
        if embedding is None:
            return self._build_result(self.STATUS_NO_FACE, None, 0.0, 0.0, 0.0)

        # 2. Search FAISS index using top-k vector aggregation & candidate margin tracking
        driver_id, top1_score, top2_score, margin, match_count = self.faiss_manager.search_top_k(
            embedding,
            top_k=RECOGNITION_TOP_K,
            threshold=self.threshold,
        )
        self.last_score = round(top1_score, 3)
        self.last_top2_score = round(top2_score, 3)
        self.last_margin = round(margin, 3)

        # 3. Check similarity threshold (>= 0.60) AND minimum match margin (>= 0.08)
        if driver_id is not None and top1_score >= self.threshold and margin >= self.min_margin:
            pred_status = self.STATUS_CONFIRMED
            pred_driver = driver_id
        else:
            pred_status = self.STATUS_UNKNOWN
            pred_driver = None

        # 4. Append to temporal voting buffer
        self.voting_buffer.append((pred_driver, top1_score, top2_score, margin, pred_status))

        # 5. Perform temporal voting aggregation
        return self._aggregate_votes()

    def _aggregate_votes(self) -> dict:
        """Aggregate sliding buffer votes to confirm identity or detect driver changes."""
        if not self.voting_buffer:
            return self._build_result(self.STATUS_VERIFYING, None, 0.0, 0.0, 0.0)

        # If buffer contains MULTIPLE_FACES entries
        multiple_count = sum(1 for item in self.voting_buffer if item[4] == self.STATUS_MULTIPLE_FACES)
        if multiple_count >= len(self.voting_buffer) / 2:
            self.current_status = self.STATUS_MULTIPLE_FACES
            self.current_driver_id = None
            return self._build_result(self.STATUS_MULTIPLE_FACES, None, 0.0, 0.0, 0.0)

        # Count driver_id occurrences in voting window
        driver_counts = {}
        total_scores = {}
        unknown_count = 0

        for driver_id, score, top2, margin, status in self.voting_buffer:
            if status == self.STATUS_UNKNOWN or driver_id is None:
                unknown_count += 1
            else:
                driver_counts[driver_id] = driver_counts.get(driver_id, 0) + 1
                total_scores[driver_id] = total_scores.get(driver_id, 0.0) + score

        total_frames = len(self.voting_buffer)

        # Check for confirmed driver with required vote ratio (>= 60%) in voting window
        for d_id, count in driver_counts.items():
            if count >= max(2, int(round(total_frames * self.vote_ratio))):
                avg_score = total_scores[d_id] / count
                if self.current_driver_id != d_id:
                    logger.info("🚗 Driver identity switch confirmed: driver_id=%d (avg score: %.3f)", d_id, avg_score)
                self.current_driver_id = d_id
                self.current_status = self.STATUS_CONFIRMED
                return self._build_result(self.STATUS_CONFIRMED, d_id, avg_score, self.last_top2_score, self.last_margin)

        # If majority of window is unknown
        if unknown_count >= int(round(total_frames * self.vote_ratio)):
            if self.current_driver_id is not None:
                logger.info("⚠️ Driver identity switched to UNKNOWN_DRIVER")
            self.current_driver_id = None
            self.current_status = self.STATUS_UNKNOWN
            return self._build_result(self.STATUS_UNKNOWN, None, self.last_score, self.last_top2_score, self.last_margin)

        # If window is still collecting/inconsistent
        self.current_status = self.STATUS_VERIFYING
        return self._build_result(self.STATUS_VERIFYING, self.current_driver_id, self.last_score, self.last_top2_score, self.last_margin)

    def _build_result(self, status: str, driver_id: int | None, score: float, top2: float, margin: float) -> dict:
        return {
            'status': status,
            'driver_id': driver_id,
            'similarity_score': round(float(score), 3),
            'top2_score': round(float(top2), 3),
            'margin': round(float(margin), 3),
            'confidence': round(max(0.0, min(1.0, float(score))), 3),
        }

    def reset(self):
        """Reset temporal voting state."""
        self.voting_buffer.clear()
        self.current_driver_id = None
        self.current_status = self.STATUS_VERIFYING
        self.last_score = 0.0
        self.last_top2_score = 0.0
        self.last_margin = 0.0
