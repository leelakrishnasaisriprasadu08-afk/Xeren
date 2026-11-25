"""File reading tool with UTF-8 decoding, line slicing, safe binary detection, and secret redaction."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from xeren.plugins.file.tools.security import FileSecurityTool

logger = logging.getLogger("xeren.plugins.file.tools.reader")


class FileReaderTool:
    """Safely reads file contents within workspace security constraints."""

    def __init__(self, security_tool: Optional[FileSecurityTool] = None) -> None:
        self.security = security_tool or FileSecurityTool()

    @staticmethod
    def is_binary_file(file_path: Path, sample_size: int = 4096) -> bool:
        """Heuristic check to identify binary files and prevent binary injection into LLM context."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(sample_size)
                if not chunk:
                    return False
                # Standard heuristic: presence of null bytes indicates binary data
                if b"\x00" in chunk:
                    return True
                # Check ratio of non-text bytes
                text_characters = bytes(range(32, 127)) + b"\n\r\t\b"
                non_text = chunk.translate(None, text_characters)
                return len(non_text) / len(chunk) > 0.30
        except Exception:
            return False

    def read_file(
        self,
        raw_path: str,
        encoding: str = "utf-8",
        max_size_bytes: Optional[int] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        redaction_enabled: bool = True,
    ) -> Dict[str, Any]:
        """Read and decode file contents safely.

        If a binary file is detected, returns metadata and a safe warning without
        decoding raw binary bytes into text.
        """
        # 1. Validate path
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=True)

        if not target_path.is_file():
            raise IsADirectoryError(f"Target path '{raw_path}' is a directory, not a regular file")

        # 2. Check file size limits before reading
        file_size = target_path.stat().st_size
        self.security.validate_size(file_size, limit_override=max_size_bytes)

        # 3. Check for binary file
        if self.is_binary_file(target_path):
            logger.info("Binary file detected at '%s'; suppressing raw text decoding", raw_path)
            return {
                "success": True,
                "content": None,
                "is_binary": True,
                "bytes_read": file_size,
                "warning": f"Binary file detected ({file_size} bytes). Raw content was not decoded into text.",
                "redacted_secrets": False,
                "path": self.security.get_relative_path(target_path),
            }

        # 4. Read text content with specified encoding
        try:
            with open(target_path, "r", encoding=encoding, errors="replace") as f:
                if line_start is not None or line_end is not None:
                    lines = f.readlines()
                    total_lines = len(lines)
                    start_idx = max(0, (line_start - 1)) if line_start else 0
                    end_idx = min(total_lines, line_end) if line_end else total_lines
                    selected_lines = lines[start_idx:end_idx]
                    content = "".join(selected_lines)
                else:
                    content = f.read()
        except Exception as err:
            logger.error("Failed to read text from '%s': %s", raw_path, err)
            raise OSError(f"Could not read file '{raw_path}' with encoding '{encoding}': {err}") from err

        # 5. Best-effort secret redaction
        sanitized_content, was_redacted = self.security.redact_secrets_if_enabled(
            content, enabled=redaction_enabled
        )

        return {
            "success": True,
            "content": sanitized_content,
            "is_binary": False,
            "bytes_read": len(content.encode(encoding, errors="replace")),
            "warning": None,
            "redacted_secrets": was_redacted,
            "path": self.security.get_relative_path(target_path),
        }


__all__ = ["FileReaderTool"]
