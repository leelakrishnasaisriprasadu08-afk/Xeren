"""Model registry and factory for managing and instantiating LLM providers."""

import threading
from typing import Dict, List, Type

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.errors import ProviderNotRegisteredError


class ModelRegistry:
    """Thread-safe registry for LLM provider adapters."""

    _lock = threading.Lock()
    _providers: Dict[str, Type[BaseLLM]] = {}

    @classmethod
    def register(cls, provider_name: str, adapter_cls: Type[BaseLLM]) -> None:
        """Register a new LLM provider adapter."""
        normalized_name = provider_name.strip().lower()
        if not issubclass(adapter_cls, BaseLLM):
            raise TypeError(f"Adapter class {adapter_cls} must subclass BaseLLM")
        with cls._lock:
            cls._providers[normalized_name] = adapter_cls

    @classmethod
    def get(cls, provider_name: str) -> Type[BaseLLM]:
        """Retrieve an adapter class for the given provider."""
        normalized_name = provider_name.strip().lower()
        with cls._lock:
            adapter_cls = cls._providers.get(normalized_name)
            if adapter_cls is None:
                available = ", ".join(cls._providers.keys()) or "none"
                raise ProviderNotRegisteredError(
                    f"Provider '{provider_name}' is not registered. Available providers: {available}"
                )
            return adapter_cls

    @classmethod
    def create(cls, config: ModelConfig) -> BaseLLM:
        """Factory method to instantiate an adapter from a ModelConfig."""
        adapter_cls = cls.get(config.provider)
        return adapter_cls(config)

    @classmethod
    def list_providers(cls) -> List[str]:
        """Return a list of all registered provider names."""
        with cls._lock:
            return sorted(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (primarily for testing)."""
        with cls._lock:
            cls._providers.clear()
