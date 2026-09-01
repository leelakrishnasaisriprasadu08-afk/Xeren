"""Core data structures for documents, chunks, and metadata in RAG."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Structured metadata associated with a document or chunk."""

    source: str = Field(..., description="File path, URL, or origin identifier")
    title: Optional[str] = Field(default=None, description="Document title if available")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when document was created/ingested",
    )
    mime_type: Optional[str] = Field(default=None, description="MIME type of the source")
    file_size: Optional[int] = Field(default=None, ge=0, description="Size in bytes")
    checksum: Optional[str] = Field(default=None, description="SHA-256 content checksum")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary user metadata")


class Document(BaseModel):
    """An ingested raw or normalized document."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the document",
    )
    content: str = Field(..., description="Full text content of the document")
    metadata: DocumentMetadata = Field(..., description="Metadata describing the document")
    doc_type: str = Field(default="text", description="Document type tag")

    @classmethod
    def from_text(
        cls,
        text: str,
        source: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "Document":
        """Convenience constructor from raw text string."""
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        meta = DocumentMetadata(
            source=source,
            title=title,
            checksum=checksum,
            file_size=len(text.encode("utf-8")),
            extra=extra or {},
            **kwargs,
        )
        return cls(id=doc_id or str(uuid.uuid4()), content=text, metadata=meta)


class DocumentChunk(BaseModel):
    """A sliced segment of a document produced by a chunker with complete provenance."""

    chunk_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this chunk",
    )
    document_id: str = Field(..., description="Identifier of the source parent document")
    content: str = Field(..., description="Text content of this chunk")
    chunk_index: int = Field(..., ge=0, description="0-indexed position within parent document")
    total_chunks: int = Field(default=1, ge=1, description="Total chunks for parent document")
    start_char_index: Optional[int] = Field(
        default=None, ge=0, description="Starting character offset in parent document"
    )
    end_char_index: Optional[int] = Field(
        default=None, ge=0, description="Ending character offset in parent document"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Merged chunk metadata")
    character_count: int = Field(default=0, ge=0, description="Number of characters in chunk")
    token_count: Optional[int] = Field(default=None, ge=0, description="Estimated token count")
    checksum: str = Field(default="", description="SHA-256 checksum of the chunk text")

    def model_post_init(self, __context: Any) -> None:
        if not self.character_count:
            self.character_count = len(self.content)
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.token_count is None:
            self.token_count = max(1, len(self.content) // 4)
