"""Configuration schemas for RAG embedding models."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class EmbeddingConfig(BaseModel):
    """Configuration options for an embedding model provider."""

    model_id: str = Field(..., description="Model identifier (e.g. 'nomic-embed-text', 'bge-large-en-v1.5')")
    provider: str = Field(..., description="Provider identifier (e.g. 'local_openweight', 'mock')")
    dimension: Optional[int] = Field(default=None, gt=0, description="Expected vector embedding dimensionality")
    batch_size: int = Field(default=32, gt=0, description="Maximum batch size for inference requests")
    api_base: Optional[str] = Field(
        default="http://localhost:11434/v1",
        description="Endpoint URL for local embedding server",
    )
    api_key: Optional[str] = Field(default=None, description="API authorization key if required")
    timeout_seconds: float = Field(default=60.0, gt=0.0, description="Request timeout in seconds")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific parameters")

    @field_validator("model_id", "provider")
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("String field must not be empty.")
        return v.strip()
