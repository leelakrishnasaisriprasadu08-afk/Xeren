"""Markdown file loader with YAML/metadata frontmatter extraction."""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from xeren.rag.document import Document, DocumentMetadata
from xeren.rag.errors import DocumentLoadingError
from xeren.rag.loaders.base import BaseDocumentLoader


class MarkdownLoader(BaseDocumentLoader):
    """Loads Markdown files (.md, .markdown, .mdx) with metadata extraction."""

    SUPPORTED_EXTENSIONS = {".md", ".markdown", ".mdx"}

    def supports(self, source: Union[str, Path]) -> bool:
        return Path(source).suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _extract_frontmatter(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Extract key-value frontmatter bounded by --- at file start."""
        if not text.startswith("---"):
            return text, {}

        match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
        if not match:
            return text, {}

        frontmatter_raw = match.group(1)
        body = match.group(2)
        meta: Dict[str, Any] = {}

        for line in frontmatter_raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip("\"'")

        return body, meta

    def _extract_headings(self, text: str) -> List[str]:
        """Extract top-level markdown headings."""
        headings = []
        for line in text.splitlines():
            match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if match:
                headings.append(match.group(2).strip())
        return headings

    def load(self, source: Union[str, Path]) -> List[Document]:
        path = Path(source)
        if not path.is_file():
            raise DocumentLoadingError(f"File not found: {source}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = path.read_text(encoding="latin-1")
            except Exception as err:
                raise DocumentLoadingError(
                    f"Failed to decode markdown file {path}: {err}", raw_error=err
                ) from err
        except Exception as err:
            raise DocumentLoadingError(f"Failed to read file {path}: {err}", raw_error=err) from err

        body, frontmatter = self._extract_frontmatter(raw_text)
        headings = self._extract_headings(body)
        title = frontmatter.get("title") or (headings[0] if headings else path.stem)

        stat = path.stat()
        checksum = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        extra_meta = dict(frontmatter)
        extra_meta.update({
            "headings": headings,
            "has_frontmatter": bool(frontmatter),
            "filename": path.name,
        })

        meta = DocumentMetadata(
            source=str(path.resolve()),
            title=str(title),
            file_size=stat.st_size,
            checksum=checksum,
            mime_type="text/markdown",
            extra=extra_meta,
        )

        return [Document(content=body, metadata=meta, doc_type="markdown")]
