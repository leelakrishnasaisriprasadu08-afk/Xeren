"""DocumentManager handling physical raw file storage and hash verification."""

import hashlib
import os
from pathlib import Path
from typing import Optional

from xeren.rag.knowledge_db.config import KnowledgeDBConfig


class DocumentManager:
    """Manages raw document content files on disk with SHA-256 integrity."""

    def __init__(self, config: KnowledgeDBConfig) -> None:
        self.config = config

    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of text content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def store_document_content(self, document_id: str, version: int, content: str) -> str:
        """Atomically persist raw text file in primary documents store.

        Returns relative path from primary directory.
        """
        doc_dir = self.config.primary_docs_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        target_file = doc_dir / f"v{version}.txt"
        tmp_file = doc_dir / f"v{version}.tmp"

        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(content)

        os.replace(tmp_file, target_file)

        # Return path relative to primary dir
        return str(target_file.relative_to(self.config.primary_dir))

    def read_document_content(self, relative_path: str) -> Optional[str]:
        """Read content from primary storage given a relative path."""
        target_file = self.config.primary_dir / relative_path
        if not target_file.exists():
            return None
        with open(target_file, "r", encoding="utf-8") as f:
            return f.read()

    def delete_document_files(self, document_id: str) -> None:
        """Remove raw storage files for a document."""
        doc_dir = self.config.primary_docs_dir / document_id
        if doc_dir.exists():
            for child in doc_dir.iterdir():
                if child.is_file():
                    child.unlink()
            doc_dir.rmdir()
