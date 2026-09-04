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

# Register default providers
ModelRegistry.register("mock", MockLLM)
ModelRegistry.register("local_openweight", LocalOpenWeightAdapter)
ModelRegistry.register("local", LocalOpenWeightAdapter)
ModelRegistry.register("ollama", LocalOpenWeightAdapter)
ModelRegistry.register("vllm", LocalOpenWeightAdapter)

__all__ = [
    # Base interfaces
    "BaseLLM",
    "BaseEmbeddingModel",
    # Registry & Factory
    "ModelRegistry",
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
