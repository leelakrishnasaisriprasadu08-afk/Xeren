"""Exception hierarchy for the Xeren RAG ingestion pipeline."""

from typing import Any, Optional


class RAGError(Exception):
    """Base exception for all RAG-related errors."""

    def __init__(self, message: str, raw_error: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.raw_error = raw_error

    def __str__(self) -> str:
        if self.raw_error:
            return f"{self.message} (Details: {self.raw_error})"
        return self.message


class DocumentLoadingError(RAGError):
    """Raised when loading or reading a document fails."""
    pass


class UnsupportedFormatError(RAGError):
    """Raised when no suitable loader is registered for the document format."""
    pass


class NormalizationError(RAGError):
    """Raised when text normalization fails."""
    pass


class ChunkingError(RAGError):
    """Raised when splitting a document into chunks fails."""
    pass


class PipelineExecutionError(RAGError):
    """Raised when pipeline execution encounters an unrecoverable failure."""
    pass
