"""Public exports for Cache-Augmented Generation (CAG) subsystem."""

from xeren.rag.cag.engine import CAGRetrievalEngine
from xeren.rag.cag.types import (
    CachedContextEntry,
    CachePolicy,
    CacheStats,
)

__all__ = [
    "CAGRetrievalEngine",
    "CachedContextEntry",
    "CachePolicy",
    "CacheStats",
]
