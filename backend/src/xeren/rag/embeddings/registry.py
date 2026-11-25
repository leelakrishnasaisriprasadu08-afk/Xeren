"""Thread-safe registry and factory for embedding model adapters."""

import threading
from typing import Dict, List, Type

from xeren.models.errors import ProviderNotRegisteredError
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.embeddings.config import EmbeddingConfig


class EmbeddingRegistry:
    """Thread-safe registry for embedding model adapters."""

    _lock = threading.Lock()
    _providers: Dict[str, Type[BaseEmbeddingModel]] = {}

    @classmethod
    def register(cls, provider_name: str, adapter_cls: Type[BaseEmbeddingModel]) -> None:
        """Register an embedding adapter class under a provider name."""
        normalized = provider_name.strip().lower()
        if not issubclass(adapter_cls, BaseEmbeddingModel):
            raise TypeError(f"Adapter class {adapter_cls} must subclass BaseEmbeddingModel")
        with cls._lock:
            cls._providers[normalized] = adapter_cls

    @classmethod
    def get(cls, provider_name: str) -> Type[BaseEmbeddingModel]:
        """Retrieve the adapter class for the given provider."""
        normalized = provider_name.strip().lower()
        with cls._lock:
            adapter_cls = cls._providers.get(normalized)
            if adapter_cls is None:
                available = ", ".join(cls._providers.keys()) or "none"
                raise ProviderNotRegisteredError(
                    f"Embedding provider '{provider_name}' is not registered. Available: {available}"
                )
            return adapter_cls

    @classmethod
    def create(cls, config: EmbeddingConfig) -> BaseEmbeddingModel:
        """Instantiate an embedding model adapter from an EmbeddingConfig."""
        adapter_cls = cls.get(config.provider)
        return adapter_cls(config)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered embedding provider names."""
        with cls._lock:
            return sorted(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers."""
        with cls._lock:
            cls._providers.clear()
