"""Public exports and provider registrations for RAG embeddings."""

from xeren.rag.embeddings.base import BaseEmbeddingModel, EmbeddedChunk
from xeren.rag.embeddings.config import EmbeddingConfig
from xeren.rag.embeddings.providers.local_openweight import LocalOpenWeightEmbeddingAdapter
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.embeddings.registry import EmbeddingRegistry

# Auto-register built-in providers
EmbeddingRegistry.register("mock", MockEmbeddingModel)
EmbeddingRegistry.register("local_openweight", LocalOpenWeightEmbeddingAdapter)
EmbeddingRegistry.register("local", LocalOpenWeightEmbeddingAdapter)
EmbeddingRegistry.register("ollama", LocalOpenWeightEmbeddingAdapter)
EmbeddingRegistry.register("vllm", LocalOpenWeightEmbeddingAdapter)
EmbeddingRegistry.register("tei", LocalOpenWeightEmbeddingAdapter)

__all__ = [
    "BaseEmbeddingModel",
    "EmbeddedChunk",
    "EmbeddingConfig",
    "EmbeddingRegistry",
    "MockEmbeddingModel",
    "LocalOpenWeightEmbeddingAdapter",
]
