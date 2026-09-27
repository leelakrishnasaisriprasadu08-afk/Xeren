"""Schemas for the Xeren Knowledge/RAG Plugin reusing core RAG types."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.document import Document, DocumentChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult


class KnowledgeOperation(str, Enum):
    """Operation mode for Knowledge Plugin execution."""

    QUERY = "query"
    INGEST = "ingest"


class RetrievalMode(str, Enum):
    """Search retrieval strategy."""

    HYBRID = "hybrid"
    DENSE = "dense"
    KEYWORD = "keyword"


class KnowledgeInput(BaseModel):
    """Input payload for Knowledge/RAG Plugin operations."""

    query: Optional[str] = Field(default=None, description="Query string for knowledge retrieval")
    operation: KnowledgeOperation = Field(
        default=KnowledgeOperation.QUERY,
        description="Target operation: 'query' (search/retrieval) or 'ingest' (add to knowledge base)",
    )
    top_k: int = Field(default=5, ge=1, le=100, description="Candidate retrieval count")
    top_n: Optional[int] = Field(default=5, ge=1, le=100, description="Reranked selection budget")
    retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.HYBRID,
        description="Retrieval strategy: hybrid (dense + BM25), dense (vector), or keyword (BM25)",
    )
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum score threshold for retrieved results")
    filter: Optional[MetadataFilter] = Field(default=None, description="Metadata filtering conditions")
    include_context: bool = Field(default=True, description="Whether to assemble grounded context with citations")
    include_provenance: bool = Field(default=True, description="Whether to include full citation provenance mapping")

    # Ingestion inputs
    documents: Optional[List[Document]] = Field(default=None, description="List of Document objects to ingest")
    texts: Optional[List[str]] = Field(default=None, description="List of raw text strings to ingest")
    source: str = Field(default="knowledge_ingest", description="Source identifier tag for ingested texts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary caller metadata")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_operation_inputs(self) -> "KnowledgeInput":
        if self.operation == KnowledgeOperation.QUERY:
            if not self.query or not self.query.strip():
                raise ValueError("Knowledge retrieval operation requires a non-empty 'query' string.")
        elif self.operation == KnowledgeOperation.INGEST:
            if not self.documents and not self.texts:
                raise ValueError("Knowledge ingestion operation requires either 'documents' or 'texts' to index.")
        return self


class KnowledgeResult(BaseModel):
    """Structured result returned by the Knowledge/RAG Plugin."""

    operation: KnowledgeOperation = Field(..., description="Executed operation type")
    query: Optional[str] = Field(default=None, description="Original query if operation was query")
    retrieved_chunks: List[DocumentChunk] = Field(
        default_factory=list,
        description="Document chunks retrieved and selected from knowledge base",
    )
    ranked_results: List[SearchResult] = Field(
        default_factory=list,
        description="Scored SearchResult candidates after reranking",
    )
    context: Optional[GroundedContext] = Field(
        default=None,
        description="Assembled grounded context block with security sanitization and prompt injection delimiters",
    )
    provenance: List[Citation] = Field(
        default_factory=list,
        description="Ordered citation references linking extracted knowledge to source chunks",
    )
    retrieval_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Relevance scores mapped by chunk_id",
    )
    knowledge_gaps: List[str] = Field(
        default_factory=list,
        description="Identified topics or concepts where knowledge coverage was insufficient",
    )
    inserted_chunk_ids: List[str] = Field(
        default_factory=list,
        description="Chunk IDs created and indexed during an ingestion operation",
    )
    execution_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics (latency_ms, candidates_count, selected_count, mode)",
    )
    success: bool = Field(default=True, description="Whether the operation succeeded")

    model_config = {"arbitrary_types_allowed": True}


__all__ = [
    "KnowledgeOperation",
    "RetrievalMode",
    "KnowledgeInput",
    "KnowledgeResult",
]
