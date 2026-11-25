"""Native CPU-optimized local vector index using NumPy matrix multiplication."""

import logging
import os
from pathlib import Path
import threading
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine

logger = logging.getLogger("xeren.rag.knowledge_db.indexing")


class NativeLocalVectorIndex(IVectorIndexEngine):
    """High-speed local CPU vector index.

    Partitions dense vectors by model_id. Normalizes rows and evaluates
    cosine similarity via vectorized dot products without server overhead.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir
        self._lock = threading.RLock()
        # model_id -> chunk_id -> List[float]
        self._vectors: Dict[str, Dict[str, List[float]]] = {}
        # model_id -> (chunk_ids: List[str], matrix: np.ndarray normalized)
        self._matrices: Dict[str, Tuple[List[str], np.ndarray]] = {}
        self._dirty: Dict[str, bool] = {}

    def index_vectors(
        self,
        model_id: str,
        dimension: int,
        vectors: Dict[str, List[float]],
    ) -> None:
        """Insert or update vectors under a model identifier."""
        with self._lock:
            if model_id not in self._vectors:
                self._vectors[model_id] = {}
            for cid, vec in vectors.items():
                if len(vec) == dimension:
                    self._vectors[model_id][cid] = vec
            self._dirty[model_id] = True

    def search_vectors(
        self,
        model_id: str,
        query_vector: List[float],
        top_k: int = 5,
        candidate_chunk_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Perform vectorized cosine similarity search."""
        with self._lock:
            if model_id not in self._vectors or not self._vectors[model_id]:
                return []

            self._ensure_matrix(model_id)
            if model_id not in self._matrices:
                return []

            chunk_ids, matrix = self._matrices[model_id]
            if len(chunk_ids) == 0:
                return []

            q = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q)
            if q_norm == 0.0:
                return []
            q_normed = q / q_norm

            # Matrix shape: (N, D), q_normed: (D,) -> similarities: (N,)
            scores = np.dot(matrix, q_normed)

            results: List[Tuple[str, float]] = []
            for cid, score in zip(chunk_ids, scores):
                if candidate_chunk_ids is not None and cid not in candidate_chunk_ids:
                    continue
                results.append((cid, float(score)))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

    def delete_vectors(self, model_id: str, chunk_ids: List[str]) -> int:
        """Remove vectors for given chunk IDs."""
        with self._lock:
            if model_id not in self._vectors:
                return 0
            deleted = 0
            for cid in chunk_ids:
                if cid in self._vectors[model_id]:
                    del self._vectors[model_id][cid]
                    deleted += 1
            if deleted > 0:
                self._dirty[model_id] = True
            return deleted

    def count(self, model_id: Optional[str] = None) -> int:
        """Count indexed vectors."""
        with self._lock:
            if model_id is not None:
                return len(self._vectors.get(model_id, {}))
            return sum(len(v) for v in self._vectors.values())

    def snapshot(self, target_directory: Path) -> Path:
        """Persist a compressed snapshot of all vector matrices."""
        with self._lock:
            target_directory.mkdir(parents=True, exist_ok=True)
            snapshot_file = target_directory / "vectors_snapshot.npz"
            tmp_file = target_directory / "vectors_snapshot_tmp.npz"

            export_data: Dict[str, Any] = {}
            for model_id, vec_map in self._vectors.items():
                cids = list(vec_map.keys())
                data = list(vec_map.values())
                export_data[f"{model_id}__ids"] = np.array(cids, dtype=object)
                export_data[f"{model_id}__vecs"] = (
                    np.array(data, dtype=np.float32) if data else np.empty((0, 0), dtype=np.float32)
                )

            np.savez_compressed(str(tmp_file), **export_data)
            os.replace(tmp_file, snapshot_file)
            return snapshot_file

    def restore(self, snapshot_path: Path) -> None:
        """Restore in-memory vector state from a snapshot archive."""
        with self._lock:
            if not snapshot_path.exists():
                return
            data = np.load(str(snapshot_path), allow_pickle=True)
            self._vectors.clear()
            self._matrices.clear()
            self._dirty.clear()

            # Find all model_ids by reading keys ending in '__ids'
            for key in data.files:
                if key.endswith("__ids"):
                    model_id = key[:-5]
                    ids = data[key]
                    vecs = data[f"{model_id}__vecs"]
                    self._vectors[model_id] = {
                        str(cid): vec.tolist() for cid, vec in zip(ids, vecs)
                    }
                    self._dirty[model_id] = True

    def clear(self) -> None:
        """Reset state."""
        with self._lock:
            self._vectors.clear()
            self._matrices.clear()
            self._dirty.clear()

    def _ensure_matrix(self, model_id: str) -> None:
        """Build normalized matrix for vectorized search."""
        if not self._dirty.get(model_id, True):
            return

        vec_map = self._vectors.get(model_id, {})
        if not vec_map:
            self._matrices.pop(model_id, None)
            self._dirty[model_id] = False
            return

        cids = list(vec_map.keys())
        raw_mat = np.array(list(vec_map.values()), dtype=np.float32)

        norms = np.linalg.norm(raw_mat, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized_mat = raw_mat / norms

        self._matrices[model_id] = (cids, normalized_mat)
        self._dirty[model_id] = False
