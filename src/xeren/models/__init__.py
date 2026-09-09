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

import os
from typing import Any, Optional

# Register default providers (local, open-weight, and OpenAI-compatible cloud APIs)
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

    Automatically resolves configuration from environment variables (.env):
      - Provider: LLM_PROVIDER (e.g. 'ollama', 'groq', 'openai', 'deepseek', 'mock')
      - Model: LLM_MODEL (e.g. 'llama3.2', 'llama-3.3-70b-versatile', 'gpt-4o-mini')
      - API Key: LLM_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY
      - API Base: LLM_API_BASE, OLLAMA_HOST
    """
    # 1. Determine provider
    effective_provider = provider or os.getenv("LLM_PROVIDER")
    if not effective_provider:
        if os.getenv("GROQ_API_KEY"):
            effective_provider = "groq"
        elif os.getenv("OPENAI_API_KEY"):
            effective_provider = "openai"
        elif os.getenv("DEEPSEEK_API_KEY"):
            effective_provider = "deepseek"
        else:
            effective_provider = "ollama"

    # 2. Determine model_id
    effective_model = model_id or os.getenv("LLM_MODEL")
    if not effective_model:
        defaults = {
            "groq": "llama-3.3-70b-versatile",
            "openai": "gpt-4o-mini",
            "deepseek": "deepseek-chat",
            "ollama": "llama3.2",
            "local": "llama3.2",
            "local_openweight": "llama3.2",
            "lmstudio": "local-model",
            "mock": "mock-model",
        }
        effective_model = defaults.get(effective_provider.lower(), "llama3.2")

    config = ModelConfig(
        model_id=effective_model,
        provider=effective_provider,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        api_key=api_key,
        api_base=api_base,
        extra_params=extra_params,
    )

    return ModelRegistry.create(config)

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
