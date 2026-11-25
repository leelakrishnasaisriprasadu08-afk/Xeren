"""Vector indexing components for Xeren Sovereign Knowledge DB."""

from xeren.rag.knowledge_db.indexing.base import IVectorIndexEngine
from xeren.rag.knowledge_db.indexing.local_numpy import NativeLocalVectorIndex

__all__ = ["IVectorIndexEngine", "NativeLocalVectorIndex"]
