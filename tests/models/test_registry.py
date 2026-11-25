"""Unit tests for the ModelRegistry and provider factory."""

import pytest

from xeren.models.base import BaseLLM
from xeren.models.config import LocalModelConfig, ModelConfig
from xeren.models.errors import ProviderNotRegisteredError
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.models.providers.mock import MockLLM
from xeren.models.registry import ModelRegistry


def test_registered_default_providers() -> None:
    providers = ModelRegistry.list_providers()
    assert "mock" in providers
    assert "local_openweight" in providers
    assert "local" in providers
    assert "ollama" in providers
    assert "vllm" in providers


def test_registry_create_mock() -> None:
    config = ModelConfig(model_id="mock-1", provider="mock")
    model = ModelRegistry.create(config)
    assert isinstance(model, MockLLM)
    assert model.config.model_id == "mock-1"


def test_registry_create_local_openweight() -> None:
    config = LocalModelConfig(model_id="llama3.2:3b", provider="local_openweight")
    model = ModelRegistry.create(config)
    assert isinstance(model, LocalOpenWeightAdapter)
    assert model.config.model_id == "llama3.2:3b"


def test_registry_unknown_provider_raises() -> None:
    config = ModelConfig(model_id="some-model", provider="unregistered_provider_xyz")
    with pytest.raises(ProviderNotRegisteredError) as exc_info:
        ModelRegistry.create(config)
    assert "unregistered_provider_xyz" in str(exc_info.value)


def test_register_invalid_class_raises() -> None:
    class NotAnLLM:
        pass

    with pytest.raises(TypeError):
        ModelRegistry.register("invalid", NotAnLLM)  # type: ignore[arg-type]
