"""Abstract base loader interface for ingesting documents."""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union

from xeren.rag.document import Document


class BaseDocumentLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    def load(self, source: Union[str, Path]) -> List[Document]:
        """Synchronously load and parse documents from a file path or source identifier."""
        pass

    async def aload(self, source: Union[str, Path]) -> List[Document]:
        """Asynchronously load and parse documents from a file path or source identifier."""
        return await asyncio.to_thread(self.load, source)

    @abstractmethod
    def supports(self, source: Union[str, Path]) -> bool:
        """Check if this loader can handle the specified file or source format."""
        pass
