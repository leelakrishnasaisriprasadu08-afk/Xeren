"""Xeren Sovereign Custom Database for RAG Knowledge Pipelines.

Strict Security Mandate:
Exclusively dedicated to RAG knowledge patterns (dense vectors, sparse lexical tokens,
code AST structures, document hierarchies, and faceted metrics).
User credentials, session secrets, and personal identity records are isolated in UserVault.
"""

from xeren.rag.stores.pattern_db.adapter import PatternVectorStore
from xeren.rag.stores.pattern_db.engine import XerenPatternDB
from xeren.rag.stores.pattern_db.indexer import PatternIndexer
from xeren.rag.stores.pattern_db.schema import (
    PatternQuery,
    PatternRecord,
    PatternSearchResult,
    PatternType,
    SecurityIsolationError,
)
from xeren.rag.stores.pattern_db.corners import (
    CornerMetrics,
    CornerQueryResult,
    MultiCornerPatternStore,
    PatternCorner,
    PatternCornerEvaluator,
    PatternQueryRouter,
    PatternSignatureNormalizer,
    ThreeFormRecord,
)
from xeren.rag.stores.pattern_db.storage_engine import PatternStorageEngine

__all__ = [
    "XerenPatternDB",
    "PatternVectorStore",
    "PatternIndexer",
    "PatternStorageEngine",
    "PatternRecord",
    "PatternType",
    "PatternQuery",
    "PatternSearchResult",
    "SecurityIsolationError",
    "PatternCorner",
    "ThreeFormRecord",
    "CornerQueryResult",
    "PatternSignatureNormalizer",
    "PatternQueryRouter",
    "MultiCornerPatternStore",
    "PatternCornerEvaluator",
    "CornerMetrics",
]
