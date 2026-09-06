"""File writing tool supporting atomic replacement, creation, targeted modification, and dry-run preview."""

import hashlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional
import uuid

from xeren.plugins.file.tools.security import FileSecurityTool

logger = logging.getLogger("xeren.plugins.file.tools.writer")


class FileWriterTool:
    """Safely creates, writes, and modifies files within workspace security boundaries."""

    def __init__(self, security_tool: Optional[FileSecurityTool] = None) -> None:
        self.security = security_tool or FileSecurityTool()

    def create_file(
        self,
        raw_path: str,
        content: str = "",
        encoding: str = "utf-8",
        overwrite: bool = False,
        create_parents: bool = True,
        atomic: bool = True,
        max_size_bytes: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create a new file. Fails if the file already exists unless overwrite=True."""
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=False)

        if target_path.exists() and not overwrite:
            raise FileExistsError(
                f"Cannot create file '{raw_path}': file already exists and overwrite is False"
            )

        return self._write_to_disk(
            target_path=target_path,
            raw_path=raw_path,
            content=content,
            encoding=encoding,
            create_parents=create_parents,
            atomic=atomic,
            max_size_bytes=max_size_bytes,
            dry_run=dry_run,
        )

    def write_file(
        self,
        raw_path: str,
        content: str = "",
        encoding: str = "utf-8",
        overwrite: bool = True,
        create_parents: bool = True,
        atomic: bool = True,
        max_size_bytes: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Write content to a file, creating it or overwriting according to the overwrite flag."""
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=False)

        if target_path.exists() and not overwrite:
            raise FileExistsError(
                f"Cannot write to '{raw_path}': file exists and overwrite is False"
            )

        return self._write_to_disk(
            target_path=target_path,
            raw_path=raw_path,
            content=content,
            encoding=encoding,
            create_parents=create_parents,
            atomic=atomic,
            max_size_bytes=max_size_bytes,
            dry_run=dry_run,
        )

    def modify_file(
        self,
        raw_path: str,
        target_content: Optional[str] = None,
        replacement: Optional[str] = None,
        new_full_content: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        encoding: str = "utf-8",
        atomic: bool = True,
        max_size_bytes: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Modify an existing file via targeted replacement, line slicing, or full content replacement."""
        target_path = self.security.resolve_and_validate_path(raw_path, must_exist=True)

        if not target_path.is_file():
            raise IsADirectoryError(f"Cannot modify '{raw_path}': path is a directory")

        # Read existing file
        with open(target_path, "r", encoding=encoding, errors="replace") as f:
            original_text = f.read()

        updated_text = original_text

        if new_full_content is not None:
            updated_text = new_full_content
        elif target_content is not None:
            if target_content not in original_text:
                raise ValueError(f"Target content block was not found in '{raw_path}'")
            replace_val = replacement if replacement is not None else ""
            updated_text = original_text.replace(target_content, replace_val, 1)
        elif line_start is not None or line_end is not None:
            lines = original_text.splitlines(keepends=True)
            total = len(lines)
            s_idx = max(0, (line_start - 1)) if line_start else 0
            e_idx = min(total, line_end) if line_end else total
            replace_val = replacement if replacement is not None else ""
            replace_lines = [replace_val] if replace_val else []
            lines[s_idx:e_idx] = replace_lines
            updated_text = "".join(lines)
        elif replacement is not None:
            # Fallback: append replacement
            updated_text = original_text + replacement

        return self._write_to_disk(
            target_path=target_path,
            raw_path=raw_path,
            content=updated_text,
            encoding=encoding,
            create_parents=False,
            atomic=atomic,
            max_size_bytes=max_size_bytes,
            dry_run=dry_run,
        )

    def _write_to_disk(
        self,
        target_path: Path,
        raw_path: str,
        content: str,
        encoding: str,
        create_parents: bool,
        atomic: bool,
        max_size_bytes: Optional[int],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Write encoded content to disk with size validation and atomic replacement."""
        encoded = content.encode(encoding, errors="replace")
        bytes_count = len(encoded)

        # Enforce size ceiling
        self.security.validate_size(bytes_count, limit_override=max_size_bytes)
        checksum = hashlib.sha256(encoded).hexdigest()
        rel_path = self.security.get_relative_path(target_path)

        if dry_run:
            logger.info("Simulated dry-run write for '%s' (%d bytes)", raw_path, bytes_count)
            return {
                "success": True,
                "path": rel_path,
                "bytes_written": bytes_count,
                "checksum_sha256": checksum,
                "dry_run": True,
            }

        # Ensure parent directory exists
        if create_parents and not target_path.parent.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if atomic:
            # Atomic write: write to temp file in the same directory, then atomic rename
            parent_dir = target_path.parent
            temp_name = f".tmp_{uuid.uuid4().hex[:8]}_{target_path.name}"
            temp_path = parent_dir / temp_name
            try:
                with open(temp_path, "wb") as f:
                    f.write(encoded)
                    f.flush()
                    os.fsync(f.fileno())
                # Atomic replacement
                os.replace(temp_path, target_path)
            except Exception as err:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
                logger.error("Atomic write failed for '%s': %s", raw_path, err)
                raise OSError(f"Failed to write file '{raw_path}': {err}") from err
        else:
            with open(target_path, "wb") as f:
                f.write(encoded)
                f.flush()

        return {
            "success": True,
            "path": rel_path,
            "bytes_written": bytes_count,
            "checksum_sha256": checksum,
            "dry_run": False,
        }


__all__ = ["FileWriterTool"]
