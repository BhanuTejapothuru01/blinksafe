"""
BlinkSafe — FAISS Vector Search Manager

Manages FAISS IndexFlatIP (Cosine Similarity on 128D L2-normalized vectors) and
persists index and vector-to-driver mappings to data/faiss/id_mapping.json.
Thread-safe for concurrent recognition and registration operations.
"""

import os
import json
import threading
import numpy as np
import faiss

from config.config import FAISS_INDEX_PATH, FAISS_MAP_PATH, FAISS_DIR, RECOGNITION_EMBEDDING_DIM, RECOGNITION_TOP_K
from utils.logger import get_logger

logger = get_logger(__name__)


class FAISSManager:
    """Encapsulates FAISS vector index, id-mapping, persistence, and top-k similarity search."""

    def __init__(
        self,
        index_path: str = FAISS_INDEX_PATH,
        map_path: str = FAISS_MAP_PATH,
        dim: int = RECOGNITION_EMBEDDING_DIM,
    ):
        self.index_path = index_path
        self.map_path = map_path
        self.dim = dim
        self.index = None
        self.id_map = []  # List of driver_ids corresponding to vector indices [0..N-1]
        self._lock = threading.Lock()

        self._ensure_dir()
        self.load_index()

    def _ensure_dir(self):
        """Ensure FAISS storage directory exists."""
        faiss_dir = os.path.dirname(self.index_path)
        if faiss_dir:
            os.makedirs(faiss_dir, exist_ok=True)

    def load_index(self) -> bool:
        """Load index and id mapping from disk, validating vector dimension match."""
        with self._lock:
            loaded_index = False
            if os.path.exists(self.index_path) and os.path.exists(self.map_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    with open(self.map_path, 'r', encoding='utf-8') as f:
                        self.id_map = json.load(f)

                    if self.index.d != self.dim:
                        logger.error("FAISS index dimension mismatch: found %d, expected %d.", self.index.d, self.dim)
                        raise ValueError(f"FAISS index dimension mismatch: found {self.index.d}, expected {self.dim}")

                    logger.info("Loaded FAISS index with %d vectors (dim=%d) from %s", self.index.ntotal, self.index.d, self.index_path)
                    loaded_index = True
                except Exception as e:
                    logger.error("Failed to load FAISS index from %s: %s. Creating new empty index.", self.index_path, e)

            if not loaded_index:
                # Create IndexFlatIP (Inner Product = Cosine Similarity for normalized vectors)
                self.index = faiss.IndexFlatIP(self.dim)
                self.id_map = []
                logger.info("Initialized new empty FAISS IndexFlatIP (dim=%d)", self.dim)
            return True

    def save_index(self) -> bool:
        """Persist current FAISS index and id mapping to disk."""
        with self._lock:
            try:
                self._ensure_dir()
                faiss.write_index(self.index, self.index_path)
                with open(self.map_path, 'w', encoding='utf-8') as f:
                    json.dump(self.id_map, f, indent=2)
                logger.info("Saved FAISS index (%d vectors) to disk.", self.index.ntotal)
                return True
            except Exception as e:
                logger.error("Failed to save FAISS index: %s", e)
                return False

    def reset_index(self) -> bool:
        """Wipe clean the FAISS index and mapping file from disk and memory."""
        with self._lock:
            try:
                self.index = faiss.IndexFlatIP(self.dim)
                self.id_map = []
                if os.path.exists(self.index_path):
                    os.remove(self.index_path)
                if os.path.exists(self.map_path):
                    os.remove(self.map_path)
                logger.info("Reset FAISS index and removed persistent index files.")
                return True
            except Exception as e:
                logger.error("Failed to reset FAISS index: %s", e)
                return False

    def add_embedding(self, embedding: np.ndarray, driver_id: int) -> int:
        """
        Add a normalized 128D vector to FAISS index and map to driver_id.

        Returns:
            faiss_id: The integer index of the vector inside FAISS.
        """
        if embedding is None or len(embedding) != self.dim:
            raise ValueError(f"Embedding must be a 1D vector of length {self.dim}")

        vec = np.asarray(embedding, dtype=np.float32).reshape(1, self.dim)
        
        with self._lock:
            faiss_id = self.index.ntotal
            self.index.add(vec)
            self.id_map.append(driver_id)
            
        self.save_index()
        logger.info("Added vector for driver_id %d to FAISS index at pos %d", driver_id, faiss_id)
        return faiss_id

    def search(self, embedding: np.ndarray, top_k: int = 1) -> tuple[int | None, float]:
        """Search top-1 nearest neighbor vector match."""
        best_driver, top1_score, _, _, _ = self.search_top_k(embedding, top_k=top_k, threshold=0.0)
        return best_driver, top1_score

    def search_top_k(
        self,
        embedding: np.ndarray,
        top_k: int = RECOGNITION_TOP_K,
        threshold: float = 0.60,
    ) -> tuple[int | None, float, float, float, int]:
        """
        Search top-k nearest vectors, aggregate matches per driver, and calculate match margin.

        Returns:
            (best_driver_id, top1_score, top2_score, margin, vote_count)
        """
        if embedding is None or len(embedding) != self.dim:
            return None, 0.0, 0.0, 0.0, 0

        with self._lock:
            if self.index is None or self.index.ntotal == 0:
                return None, 0.0, 0.0, 0.0, 0

            vec = np.asarray(embedding, dtype=np.float32).reshape(1, self.dim)
            k = min(top_k, self.index.ntotal)

            try:
                distances, indices = self.index.search(vec, k)
                if indices.size == 0 or indices[0][0] < 0:
                    return None, 0.0, 0.0, 0.0, 0

                driver_scores = {}
                driver_votes = {}

                for dist, idx in zip(distances[0], indices[0]):
                    score = float(dist)
                    if idx >= 0 and idx < len(self.id_map) and score >= threshold:
                        driver_id = self.id_map[idx]
                        driver_scores[driver_id] = driver_scores.get(driver_id, 0.0) + score
                        driver_votes[driver_id] = driver_votes.get(driver_id, 0) + 1

                if not driver_votes:
                    return None, 0.0, 0.0, 0.0, 0

                # Compute average score per driver
                driver_averages = {d: driver_scores[d] / driver_votes[d] for d in driver_votes}
                sorted_drivers = sorted(driver_averages.keys(), key=lambda d: (driver_votes[d], driver_averages[d]), reverse=True)

                best_driver = sorted_drivers[0]
                top1_score = driver_averages[best_driver]
                top1_votes = driver_votes[best_driver]

                top2_score = driver_averages[sorted_drivers[1]] if len(sorted_drivers) > 1 else 0.0
                margin = top1_score - top2_score

                return best_driver, top1_score, top2_score, margin, top1_votes

            except Exception as e:
                logger.error("FAISS search_top_k exception: %s", e)
                return None, 0.0, 0.0, 0.0, 0
