"""Registry for document loaders with automatic extension dispatch."""

from pathlib import Path
from typing import Dict, List, Optional, Type, Union

from xeren.rag.errors import UnsupportedFormatError
from xeren.rag.loaders.base import BaseDocumentLoader
from xeren.rag.loaders.json_loader import JSONLoader
from xeren.rag.loaders.markdown import MarkdownLoader
from xeren.rag.loaders.text import TextFileLoader


class LoaderRegistry:
    """Registry managing available document loaders."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._loaders: List[BaseDocumentLoader] = []
        if register_defaults:
            self._register_default_loaders()

    def _register_default_loaders(self) -> None:
        self._loaders.append(MarkdownLoader())
        self._loaders.append(JSONLoader())
        self._loaders.append(TextFileLoader())

    def register(self, loader: BaseDocumentLoader, prepend: bool = True) -> None:
        """Register a new document loader (prepended by default for priority override)."""
        if prepend:
            self._loaders.insert(0, loader)
        else:
            self._loaders.append(loader)

    def get_loader_for(self, source: Union[str, Path]) -> BaseDocumentLoader:
        """Find the first matching loader that supports the given file source."""
        for loader in self._loaders:
            if loader.supports(source):
                return loader
        raise UnsupportedFormatError(f"No registered loader supports source: {source}")

    def list_loaders(self) -> List[BaseDocumentLoader]:
        """Return all registered loader instances."""
        return list(self._loaders)
