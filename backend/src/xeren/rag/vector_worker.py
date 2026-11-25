"""Re-export Dense Vector Worker for xeren package namespace."""

from src.rag.vector_worker import (  # noqa: F401
    DEFAULT_COLLECTION,
    DEFAULT_MODEL_NAME,
    DEFAULT_STORAGE_PATH,
    DenseVectorWorker,
    mcp,
    query_embeddings,
)

__all__ = [
    "DEFAULT_COLLECTION",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_STORAGE_PATH",
    "DenseVectorWorker",
    "mcp",
    "query_embeddings",
]
