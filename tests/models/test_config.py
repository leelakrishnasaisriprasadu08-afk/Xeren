"""Unit tests for LLM configuration schemas."""

import pytest
from pydantic import ValidationError

from xeren.models.config import LocalModelConfig, ModelConfig


def test_model_config_defaults() -> None:
    config = ModelConfig(model_id="test-model", provider="mock")
    assert config.model_id == "test-model"
    assert config.provider == "mock"
    assert config.temperature == 0.7
    assert config.top_p == 1.0
    assert config.max_tokens is None
    assert config.stop_sequences == []
    assert config.timeout_seconds == 60.0
    assert config.api_key is None
    assert config.api_base is None
    assert config.extra_params == {}


def test_model_config_validation_bounds() -> None:
    # Temperature bounds
    with pytest.raises(ValidationError):
        ModelConfig(model_id="m", provider="p", temperature=-0.1)

    with pytest.raises(ValidationError):
        ModelConfig(model_id="m", provider="p", temperature=2.5)

    # Top-p bounds
    with pytest.raises(ValidationError):
        ModelConfig(model_id="m", provider="p", top_p=-0.1)

    with pytest.raises(ValidationError):
        ModelConfig(model_id="m", provider="p", top_p=1.1)

    # Empty string validation
    with pytest.raises(ValidationError):
        ModelConfig(model_id="", provider="p")

    with pytest.raises(ValidationError):
        ModelConfig(model_id="m", provider="   ")


def test_local_model_config_defaults() -> None:
    config = LocalModelConfig(model_id="llama3.2:3b")
    assert config.provider == "local_openweight"
    assert config.api_base == "http://localhost:11434/v1"
    assert config.context_window == 8192
    assert config.quantization is None
    assert config.gpu_layers is None


def test_local_model_config_custom_values() -> None:
    config = LocalModelConfig(
        model_id="mistral-7b",
        api_base="http://localhost:8000/v1",
        context_window=16384,
        quantization="q4_k_m",
        gpu_layers=33,
        temperature=0.2,
        extra_params={"seed": 42},
    )
    assert config.model_id == "mistral-7b"
    assert config.api_base == "http://localhost:8000/v1"
    assert config.context_window == 16384
    assert config.quantization == "q4_k_m"
    assert config.gpu_layers == 33
    assert config.temperature == 0.2
    assert config.extra_params == {"seed": 42}
