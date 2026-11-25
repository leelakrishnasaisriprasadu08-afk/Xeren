"""Pluggable vector index interface for Xeren Sovereign Knowledge DB."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class IVectorIndexEngine(ABC):
    """Abstract interface defining the pluggable vector index engine contract."""

    @abstractmethod
    def index_vectors(
        self,
        model_id: str,
        dimension: int,
        vectors: Dict[str, List[float]],
    ) -> None:
        """Add or update dense vectors mapped by chunk_id under a specific model."""
        pass

    @abstractmethod
    def search_vectors(
        self,
        model_id: str,
        query_vector: List[float],
        top_k: int = 5,
        candidate_chunk_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Return list of (chunk_id, cosine_similarity_score) sorted descending."""
        pass

    @abstractmethod
    def delete_vectors(self, model_id: str, chunk_ids: List[str]) -> int:
        """Delete vectors by chunk_id. Returns number of removed vectors."""
        pass

    @abstractmethod
    def count(self, model_id: Optional[str] = None) -> int:
        """Return total indexed vectors, optionally scoped to a model_id."""
        pass

    @abstractmethod
    def snapshot(self, target_directory: Path) -> Path:
        """Create a consistent snapshot of the vector index for passive backup."""
        pass

    @abstractmethod
    def restore(self, snapshot_path: Path) -> None:
        """Restore vector index state from a snapshot directory or file."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all indexed vectors."""
        pass
