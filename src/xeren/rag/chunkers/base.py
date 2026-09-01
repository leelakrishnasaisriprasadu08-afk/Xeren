"""Abstract base chunker interface for document splitting."""

from abc import ABC, abstractmethod
from typing import List

from xeren.rag.document import Document, DocumentChunk


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    @abstractmethod
    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split a document into an ordered list of DocumentChunks."""
        pass
