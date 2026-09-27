"""Configuration models for LLM providers and local models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """Configuration options for an LLM instance."""

    model_id: str = Field(..., description="Unique model identifier or checkpoint name")
    provider: str = Field(..., description="Provider name (e.g. 'local_openweight', 'mock')")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling probability")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="Maximum tokens to generate")
    stop_sequences: List[str] = Field(default_factory=list, description="Stop sequence triggers")
    timeout_seconds: float = Field(default=60.0, gt=0.0, description="Request timeout in seconds")
    api_key: Optional[str] = Field(default=None, description="API authorization key if required")
    api_base: Optional[str] = Field(default=None, description="Custom base URL for the endpoint")
    extra_params: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific additional parameters"
    )

    @field_validator("model_id", "provider")
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("String field must not be empty.")
        return v.strip()


class LocalModelConfig(ModelConfig):
    """Specialized configuration for local and open-weight models."""

    provider: str = Field(default="local_openweight", description="Provider identifier")
    api_base: Optional[str] = Field(
        default="http://localhost:11434/v1",
        description="Endpoint URL (e.g. Ollama v1, vLLM, llama.cpp server)",
    )
    context_window: int = Field(
        default=8192, gt=0, description="Total context window token capacity"
    )
    quantization: Optional[str] = Field(
        default=None, description="Quantization format (e.g. q4_k_m, fp16, awq)"
    )
    gpu_layers: Optional[int] = Field(
        default=None, ge=-1, description="Number of layers offloaded to GPU (-1 for all)"
    )
