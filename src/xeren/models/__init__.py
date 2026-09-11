"""Public exports for the Xeren LLM models subsystem."""

from xeren.models.base import BaseEmbeddingModel, BaseLLM
from xeren.models.batching import (
    Batch,
    DataCollatorForCausalLM,
    TrainingDataLoader,
)
from xeren.models.checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
)
from xeren.models.config import LocalModelConfig, ModelConfig
from xeren.models.presets import (
    MODEL_PRESETS,
    get_model_preset,
    get_presets_by_temperature_range,
    list_model_presets,
)
from xeren.models.errors import (
    AuthenticationError,
    ConfigurationError,
    ContextLengthExceededError,
    InferenceTimeoutError,
    LLMError,
    ModelNotFoundError,
    OutputParsingError,
    ProviderConnectionError,
    ProviderNotRegisteredError,
    RateLimitError,
)
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.models.providers.mock import MockLLM
from xeren.models.registry import ModelRegistry
from xeren.models.tokenizer import (
    IGNORE_INDEX,
    SPECIAL_TOKENS,
    BaseTokenizer,
    TokenizerConfig,
    XerenTokenizer,
)
from xeren.models.tiny_model import TinyCausalLM
from xeren.models.trainer import (
    ReadinessCheckReport,
    XerenTrainer,
)
from xeren.models.training_config import TrainingConfig
from xeren.models.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    Role,
    StreamChunk,
    TokenUsage,
    ToolCall,
)

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("xeren.models")

try:
    from xeren.models.providers.xeren_native import XerenNativeLLM
    XEREN_NATIVE_AVAILABLE = True
except Exception as _e:
    XerenNativeLLM = None  # type: ignore
    XEREN_NATIVE_AVAILABLE = False

# Register default providers (local, open-weight, native checkpoints, and OpenAI-compatible cloud APIs)
ModelRegistry.register("mock", MockLLM)
ModelRegistry.register("local_openweight", LocalOpenWeightAdapter)
ModelRegistry.register("local", LocalOpenWeightAdapter)
ModelRegistry.register("ollama", LocalOpenWeightAdapter)
ModelRegistry.register("vllm", LocalOpenWeightAdapter)
ModelRegistry.register("lmstudio", LocalOpenWeightAdapter)
ModelRegistry.register("openai", LocalOpenWeightAdapter)
ModelRegistry.register("groq", LocalOpenWeightAdapter)
ModelRegistry.register("deepseek", LocalOpenWeightAdapter)
ModelRegistry.register("openrouter", LocalOpenWeightAdapter)
ModelRegistry.register("together", LocalOpenWeightAdapter)
ModelRegistry.register("gemini", LocalOpenWeightAdapter)
ModelRegistry.register("google", LocalOpenWeightAdapter)

if XEREN_NATIVE_AVAILABLE and XerenNativeLLM:
    ModelRegistry.register("xeren_native", XerenNativeLLM)
    ModelRegistry.register("xeren_mini", XerenNativeLLM)
    ModelRegistry.register("xeren-mini", XerenNativeLLM)


def create_llm(
    model_id: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    temperature: float = 0.7,
    timeout_seconds: float = 60.0,
    **extra_params: Any,
) -> BaseLLM:
    """Convenience factory to instantiate and configure an LLM for Xeren.

    Defaults to Xeren-Mini (1.5B parameter model architecture) or resolves from environment variables:
      - Provider: LLM_PROVIDER (e.g. 'xeren_mini', 'ollama', 'groq', 'openai', 'deepseek', 'mock')
      - Model: LLM_MODEL (e.g. 'xeren_mini', 'xeren-mini-1.5b', 'llama3.2', 'gpt-4o-mini')
      - API Key: LLM_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY
      - API Base / Checkpoint: LLM_API_BASE, XEREN_CHECKPOINT, OLLAMA_HOST
    """
    raw_model = model_id or os.getenv("LLM_MODEL")
    raw_provider = provider or os.getenv("LLM_PROVIDER")

    # If xeren_mini or 1.5b requested explicitly or default
    is_xeren_mini = (
        (raw_model and any(k in raw_model.lower() for k in ("xeren_mini", "xeren-mini", "1.5b")))
        or (raw_provider and any(k in raw_provider.lower() for k in ("xeren_native", "xeren_mini", "xeren-mini")))
    )

    # 1. Determine provider
    if is_xeren_mini:
        # Check if local PyTorch checkpoint exists
        ckpt_path = api_base or os.getenv("XEREN_CHECKPOINT", "training/checkpoints/xeren_mini_final")
        if XEREN_NATIVE_AVAILABLE and Path(ckpt_path).exists():
            effective_provider = "xeren_native"
            effective_model = raw_model or "xeren-mini-1.5b"
        else:
            # Fallback to local openweight adapter (Ollama or OpenAI-compatible endpoint hosting 1.5b)
            effective_provider = raw_provider or "ollama"
            effective_model = raw_model or "xeren-mini-1.5b"
    else:
        effective_provider = raw_provider
        if not effective_provider:
            if os.getenv("GROQ_API_KEY"):
                effective_provider = "groq"
            elif os.getenv("OPENAI_API_KEY"):
                effective_provider = "openai"
            elif os.getenv("DEEPSEEK_API_KEY"):
                effective_provider = "deepseek"
            elif os.getenv("GEMINI_API_KEY"):
                effective_provider = "gemini"
            elif XEREN_NATIVE_AVAILABLE and Path("training/checkpoints/xeren_mini_final").exists():
                effective_provider = "xeren_native"
            else:
                effective_provider = "ollama"

        effective_model = raw_model
        if not effective_model:
            defaults = {
                "xeren_native": "xeren-mini-1.5b",
                "xeren_mini": "xeren-mini-1.5b",
                "groq": "llama-3.3-70b-versatile",
                "openai": "gpt-4o-mini",
                "deepseek": "deepseek-chat",
                "gemini": "gemini-1.5-pro",
                "ollama": "llama3.2",
                "local": "llama3.2",
                "local_openweight": "llama3.2",
                "lmstudio": "local-model",
                "mock": "mock-model",
            }
            effective_model = defaults.get(effective_provider.lower(), "xeren-mini-1.5b")

    config = ModelConfig(
        model_id=effective_model,
        provider=effective_provider,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        api_key=api_key,
        api_base=api_base,
        extra_params=extra_params,
    )

    try:
        return ModelRegistry.create(config)
    except Exception as err:
        logger.warning("Could not instantiate provider '%s' (%s), falling back to mock: %s", effective_provider, effective_model, err)
        return MockLLM(config)


__all__ = [
    # Base interfaces
    "BaseLLM",
    "BaseEmbeddingModel",
    # Registry & Factory
    "ModelRegistry",
    "create_llm",
    # Configurations
    "ModelConfig",
    "LocalModelConfig",
    "MODEL_PRESETS",
    "get_model_preset",
    "list_model_presets",
    "get_presets_by_temperature_range",
    # Types & Schemas
    "Role",
    "ChatMessage",
    "FunctionCall",
    "ToolCall",
    "TokenUsage",
    "LLMResponse",
    "StreamChunk",
    # Providers
    "MockLLM",
    "LocalOpenWeightAdapter",
    # Errors
    "LLMError",
    "ModelNotFoundError",
    "ProviderNotRegisteredError",
    "ProviderConnectionError",
    "AuthenticationError",
    "RateLimitError",
    "ContextLengthExceededError",
    "OutputParsingError",
    "ConfigurationError",
    "InferenceTimeoutError",
    # Model Training Foundation
    "TrainingConfig",
    "TinyCausalLM",
    "BaseTokenizer",
    "XerenTokenizer",
    "TokenizerConfig",
    "SPECIAL_TOKENS",
    "IGNORE_INDEX",
    "CheckpointMetadata",
    "CheckpointManager",
    "Batch",
    "DataCollatorForCausalLM",
    "TrainingDataLoader",
    "XerenTrainer",
    "ReadinessCheckReport",
]
