"""Abstract base normalizer interface for document text normalization."""

from abc import ABC, abstractmethod

from xeren.rag.document import Document


class BaseNormalizer(ABC):
    """Abstract base class for document and text normalizers."""

    @abstractmethod
    def normalize(self, document: Document) -> Document:
        """Normalize the content of a document and return an updated Document."""
        pass
