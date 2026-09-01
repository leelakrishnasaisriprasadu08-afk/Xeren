"""Plain text file loader supporting multiple text-based extensions and encodings."""

import hashlib
import os
from pathlib import Path
from typing import List, Set, Union

from xeren.rag.document import Document, DocumentMetadata
from xeren.rag.errors import DocumentLoadingError
from xeren.rag.loaders.base import BaseDocumentLoader


class TextFileLoader(BaseDocumentLoader):
    """Loads plain text files (.txt, .log, .csv, .tsv, .py, .js, .html, .css, etc.)."""

    DEFAULT_EXTENSIONS: Set[str] = {
        ".txt",
        ".text",
        ".log",
        ".csv",
        ".tsv",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".xml",
        ".yaml",
        ".yml",
    }

    def __init__(self, supported_extensions: Union[Set[str], None] = None) -> None:
        self.supported_extensions = (
            {ext.lower() for ext in supported_extensions}
            if supported_extensions
            else self.DEFAULT_EXTENSIONS
        )

    def supports(self, source: Union[str, Path]) -> bool:
        path = Path(source)
        return path.suffix.lower() in self.supported_extensions

    def load(self, source: Union[str, Path]) -> List[Document]:
        path = Path(source)
        if not path.is_file():
            raise DocumentLoadingError(f"File not found or not a valid file: {source}")

        content: str
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="latin-1")
            except Exception as err:
                raise DocumentLoadingError(
                    f"Failed to read file {path} with UTF-8 and Latin-1 fallback: {err}",
                    raw_error=err,
                ) from err
        except Exception as err:
            raise DocumentLoadingError(f"Failed to read file {path}: {err}", raw_error=err) from err

        stat = path.stat()
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

        meta = DocumentMetadata(
            source=str(path.resolve()),
            title=path.stem,
            file_size=stat.st_size,
            checksum=checksum,
            mime_type="text/plain",
            extra={"extension": path.suffix.lower(), "filename": path.name},
        )

        return [Document(content=content, metadata=meta, doc_type="text")]
