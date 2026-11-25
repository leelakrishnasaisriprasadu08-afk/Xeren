"""Search and retrieval result types."""

from typing import List, Optional
from pydantic import BaseModel, Field

from xeren.rag.document import DocumentChunk


class SearchResult(BaseModel):
    """A scored document chunk returned by a retriever or vector store."""

    chunk: DocumentChunk = Field(..., description="The retrieved DocumentChunk")
    score: float = Field(..., description="Similarity or relevance score (higher is more relevant)")
    retrieval_type: str = Field(default="dense", description="Type of retrieval (dense, sparse, hybrid)")
    vector: Optional[List[float]] = Field(default=None, description="Optional embedded vector")
