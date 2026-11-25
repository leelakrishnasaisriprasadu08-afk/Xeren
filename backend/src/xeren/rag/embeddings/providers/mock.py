"""Deterministic mock embedding provider for testing."""

import hashlib
import math
from typing import List, Optional

from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.embeddings.config import EmbeddingConfig


class MockEmbeddingModel(BaseEmbeddingModel):
    """Deterministic in-memory embedding model for unit tests."""

    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        dimension: int = 64,
    ) -> None:
        cfg = config or EmbeddingConfig(
            model_id="mock-embed",
            provider="mock",
            dimension=dimension,
        )
        super().__init__(cfg)
        self.dimension = cfg.dimension or dimension

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic unit-normalized float vector based on text hash."""
        seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        raw_values = []
        for i in range(self.dimension):
            byte_val = seed_bytes[i % len(seed_bytes)]
            val = ((byte_val + i) % 100) / 100.0 - 0.5
            raw_values.append(val)

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in raw_values)) or 1.0
        return [round(x / norm, 6) for x in raw_values]

    def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]
