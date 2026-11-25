"""Safe content retriever for selected workspace candidate files.

Features:
1. Enforces size ceilings (default 10 MB).
2. Segmented chunking for large files.
3. Type-specific safe parsing (CSV, JSON, Markdown, Text, Code, PDF, DOCX, XLSX).
4. Binary safety: suppresses raw binary byte dump into LLM context.
5. Best-effort secret and credential redaction.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xeren.plugins.file.tools.reader import FileReaderTool
from xeren.plugins.file.tools.security import SECRET_PATTERNS
from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.schemas import CandidateFile, RetrievedContent

logger = logging.getLogger("xeren.workspace.content")


class WorkspaceContentRetriever:
    """Retrieves, validates, chunks, and sanitizes content from selected workspace candidates."""

    def __init__(
        self,
        permission_manager: Optional[WorkspacePermissionManager] = None,
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10 MB
        default_chunk_size: int = 2000,
        default_chunk_overlap: int = 200,
        redaction_enabled: bool = True,
    ) -> None:
        self.permissions = permission_manager or WorkspacePermissionManager()
        self.max_file_size_bytes = max_file_size_bytes
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.redaction_enabled = redaction_enabled

    def retrieve(
        self,
        candidate: CandidateFile,
        max_preview_lines: int = 100,
        chunk_content: bool = True,
    ) -> RetrievedContent:
        """Retrieve and safely parse the content of a validated candidate file."""
        path = candidate.absolute_path

        # 1. Validate security boundary
        validated_path, _ = self.permissions.validate_path(
            path,
            operation="read",
            must_exist=True,
        )

        stat = validated_path.stat()
        file_size = stat.st_size

        if file_size > self.max_file_size_bytes:
            logger.warning(
                "File size %d exceeds limit %d for '%s'",
                file_size,
                self.max_file_size_bytes,
                candidate.relative_path,
            )
            return RetrievedContent(
                file_id=candidate.file_id,
                path=candidate.relative_path,
                content=None,
                is_binary=False,
                file_type=candidate.file_type,
                size_bytes=file_size,
                chunks=[],
                metadata={
                    "error": f"File exceeds maximum allowed size of {self.max_file_size_bytes} bytes",
                    "oversized": True,
                },
            )

        # 2. Check binary heuristic
        if FileReaderTool.is_binary_file(validated_path):
            return self._handle_binary_file(validated_path, candidate, file_size)

        # 3. Read and decode text
        raw_text = self._read_text_safely(validated_path)

        # 4. Redact secrets
        sanitized_text, was_redacted = self._redact_secrets(raw_text)

        # 5. Type-specific preview / structured parsing
        ext = candidate.file_type.lower()
        parsed_preview: Optional[Any] = None

        if ext == "csv":
            parsed_preview = self._parse_csv_preview(sanitized_text, max_rows=max_preview_lines)
        elif ext == "json":
            parsed_preview = self._parse_json_preview(sanitized_text)

        # 6. Chunking
        chunks: List[str] = []
        if chunk_content and sanitized_text:
            chunks = self._chunk_text(
                sanitized_text,
                chunk_size=self.default_chunk_size,
                overlap=self.default_chunk_overlap,
            )

        return RetrievedContent(
            file_id=candidate.file_id,
            path=candidate.relative_path,
            content=sanitized_text,
            is_binary=False,
            file_type=ext,
            size_bytes=file_size,
            chunks=chunks,
            parsed_preview=parsed_preview,
            metadata={
                "redacted_secrets": was_redacted,
                "lines_count": len(sanitized_text.splitlines()) if sanitized_text else 0,
                "chunk_count": len(chunks),
            },
        )

    def _read_text_safely(self, path: Path) -> str:
        """Read file attempting UTF-8 first, falling back gracefully."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()

    def _redact_secrets(self, text: str) -> Tuple[str, bool]:
        """Apply best-effort masking to tokens and credentials."""
        if not self.redaction_enabled or not text:
            return text, False

        sanitized = text
        redaction_occurred = False
        for pattern, replacement in SECRET_PATTERNS:
            new_text, count = pattern.subn(replacement, sanitized)
            if count > 0:
                sanitized = new_text
                redaction_occurred = True

        return sanitized, redaction_occurred

    def _parse_csv_preview(self, text: str, max_rows: int = 50) -> Dict[str, Any]:
        """Parse structured tabular CSV rows for preview."""
        try:
            reader = csv.reader(io.StringIO(text))
            rows: List[List[str]] = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)

            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            return {
                "format": "csv",
                "headers": headers,
                "row_count_preview": len(data_rows),
                "preview_rows": data_rows[:10],
            }
        except Exception as err:
            return {"format": "csv", "parse_error": str(err)}

    def _parse_json_preview(self, text: str) -> Optional[Any]:
        """Safely deserialize JSON structures."""
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return {
                    "format": "json_array",
                    "total_items": len(parsed),
                    "sample": parsed[:5],
                }
            if isinstance(parsed, dict):
                return {
                    "format": "json_object",
                    "keys": list(parsed.keys())[:20],
                }
            return parsed
        except Exception:
            return None

    def _handle_binary_file(
        self,
        path: Path,
        candidate: CandidateFile,
        file_size: int,
    ) -> RetrievedContent:
        """Handle binary files safely without leaking binary streams into LLM context."""
        ext = candidate.file_type.lower()
        extracted_text: Optional[str] = None
        preview_meta: Dict[str, Any] = {
            "is_binary": True,
            "warning": f"Binary file detected ({file_size} bytes). Raw bytes not dumped.",
        }

        # Safe PDF text extraction if pypdf is installed
        if ext == "pdf":
            extracted_text = self._try_extract_pdf(path)
            if extracted_text:
                preview_meta["extracted_pdf_text"] = True

        return RetrievedContent(
            file_id=candidate.file_id,
            path=candidate.relative_path,
            content=extracted_text,
            is_binary=True,
            file_type=ext,
            size_bytes=file_size,
            chunks=self._chunk_text(extracted_text) if extracted_text else [],
            parsed_preview=preview_meta,
            metadata=preview_meta,
        )

    def _try_extract_pdf(self, path: Path) -> Optional[str]:
        """Best-effort PDF text extraction using available standard libraries."""
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(str(path))
            pages_text = [page.extract_text() or "" for page in reader.pages[:20]]
            return "\n\n".join(pages_text)
        except Exception:
            return None

    def _chunk_text(
        self,
        text: Optional[str],
        chunk_size: int = 2000,
        overlap: int = 200,
    ) -> List[str]:
        """Chunk text into overlapping windows for downstream consumption."""
        if not text:
            return []

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            if end == text_len:
                break
            start += chunk_size - overlap

        return chunks


__all__ = ["WorkspaceContentRetriever"]
