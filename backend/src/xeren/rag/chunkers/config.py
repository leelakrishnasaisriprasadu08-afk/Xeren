"""Configuration schemas for RAG document chunkers."""

from typing import List
from pydantic import BaseModel, Field, model_validator


class ChunkingConfig(BaseModel):
    """Configuration options for text and document chunking."""

    chunk_size: int = Field(default=1000, gt=0, description="Target chunk size in characters")
    chunk_overlap: int = Field(
        default=100, ge=0, description="Overlap size in characters between adjacent chunks"
    )
    separators: List[str] = Field(
        default_factory=lambda: ["\n\n", "\n", " ", ""],
        description="Hierarchical text split separators",
    )
    strip_whitespace: bool = Field(
        default=True, description="Whether to strip whitespace from chunk boundaries"
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than chunk_size ({self.chunk_size})"
            )
        return self
