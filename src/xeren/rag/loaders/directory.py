"""Recursive directory document loader with file glob and filter patterns."""

from pathlib import Path
from typing import List, Optional, Set, Union

from xeren.rag.document import Document
from xeren.rag.errors import DocumentLoadingError
from xeren.rag.loaders.base import BaseDocumentLoader
from xeren.rag.loaders.registry import LoaderRegistry


class DirectoryLoader(BaseDocumentLoader):
    """Recursively loads supported documents from a directory."""

    DEFAULT_EXCLUDES: Set[str] = {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".venv",
        "venv",
    }

    def __init__(
        self,
        registry: Optional[LoaderRegistry] = None,
        glob_pattern: str = "**/*",
        exclude_patterns: Optional[Set[str]] = None,
        recursive: bool = True,
        ignore_hidden: bool = True,
    ) -> None:
        self.registry = registry or LoaderRegistry()
        self.glob_pattern = glob_pattern
        self.exclude_patterns = exclude_patterns or self.DEFAULT_EXCLUDES
        self.recursive = recursive
        self.ignore_hidden = ignore_hidden

    def supports(self, source: Union[str, Path]) -> bool:
        return Path(source).is_dir()

    def _should_skip(self, path: Path) -> bool:
        if self.ignore_hidden and any(part.startswith(".") for part in path.parts):
            return True
        for exclude in self.exclude_patterns:
            if exclude in path.parts or path.match(exclude):
                return True
        return False

    def load(self, source: Union[str, Path]) -> List[Document]:
        dir_path = Path(source)
        if not dir_path.is_dir():
            raise DocumentLoadingError(f"Directory not found or is not a directory: {source}")

        documents: List[Document] = []
        files = dir_path.rglob(self.glob_pattern) if self.recursive else dir_path.glob(self.glob_pattern)

        for file_path in sorted(files):
            if not file_path.is_file():
                continue
            if self._should_skip(file_path):
                continue

            try:
                loader = self.registry.get_loader_for(file_path)
                docs = loader.load(file_path)
                documents.extend(docs)
            except Exception:
                # Skip unsupported files without failing the whole directory ingestion
                continue

        return documents
