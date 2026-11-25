"""Schemas for RAG context selection, citation tracking, and grounded output."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from xeren.rag.retrieval.types import SearchResult


class Citation(BaseModel):
    """Source citation mapping for grounded LLM generation."""

    citation_id: int = Field(..., description="1-indexed reference identifier (e.g. 1 for [1])")
    source: str = Field(..., description="File path, URL, or origin of the document")
    title: Optional[str] = Field(default=None, description="Document title if present")
    header_path: Optional[str] = Field(default=None, description="Markdown header breadcrumb hierarchy")
    chunk_id: str = Field(..., description="Unique ID of the cited chunk")
    start_char_index: Optional[int] = Field(default=None, description="Starting offset in source document")
    end_char_index: Optional[int] = Field(default=None, description="Ending offset in source document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")


class ContextConfig(BaseModel):
    """Configuration options for context budget and formatting."""

    max_tokens: int = Field(default=2048, gt=0, description="Maximum token budget for retrieved context")
    max_chunks: int = Field(default=5, gt=0, description="Maximum number of chunks to include")
    min_score_threshold: float = Field(
        default=0.0, description="Minimum relevance score to be included in context"
    )
    include_header_metadata: bool = Field(
        default=True, description="Whether to include section/header breadcrumbs in citation blocks"
    )
    citation_style: Literal["bracket", "header", "markdown"] = Field(
        default="bracket", description="Citation formatting style"
    )


class GroundedContext(BaseModel):
    """Final assembled context payload ready for prompt injection."""

    formatted_text: str = Field(..., description="Grounded context string formatted for prompt injection")
    selected_chunks: List[SearchResult] = Field(
        default_factory=list, description="List of SearchResult items selected within budget"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Ordered citation references corresponding to selected chunks"
    )
    total_characters: int = Field(default=0, ge=0, description="Total characters in formatted context")
    estimated_tokens: int = Field(default=0, ge=0, description="Estimated token count of formatted context")
    has_context: bool = Field(default=False, description="True if one or more valid chunks were selected")
