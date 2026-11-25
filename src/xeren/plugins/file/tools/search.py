"""Filesystem search tool performing pattern-based filename search and text/regex content search.

Notice: This tool performs purely deterministic filesystem and line-level text operations.
It does NOT use vector databases, embeddings, chunking, or semantic RAG components,
which belong strictly to Xeren's own RAG/Knowledge system.
"""

import logging
from pathlib import Path
import re
from typing import List, Optional, Set

from xeren.plugins.file.schemas import SearchResultItem
from xeren.plugins.file.tools.reader import FileReaderTool
from xeren.plugins.file.tools.security import FileSecurityTool

logger = logging.getLogger("xeren.plugins.file.tools.search")

# Standard noise folders ignored during searches unless explicitly requested
DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".idea",
    ".vscode",
    ".pytest_cache",
}


class FileSearchTool:
    """Performs filename pattern and text/regex content search across the workspace."""

    def __init__(self, security_tool: Optional[FileSecurityTool] = None) -> None:
        self.security = security_tool or FileSecurityTool()

    def search(
        self,
        raw_path: Optional[str] = None,
        pattern: Optional[str] = None,
        search_content: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100,
        encoding: str = "utf-8",
    ) -> List[SearchResultItem]:
        """Search workspace files by filename glob and/or line content matches."""
        target_dir = (
            self.security.resolve_and_validate_path(raw_path, must_exist=True)
            if raw_path
            else self.security.workspace_dir
        )

        if not target_dir.is_dir():
            raise NotADirectoryError(f"Search root '{raw_path or '.'}' is not a directory")

        results: List[SearchResultItem] = []
        glob_pat = pattern or "*"

        # Prepare regex if content search is requested
        content_regex: Optional[re.Pattern[str]] = None
        if search_content:
            flags = 0 if case_sensitive else re.IGNORECASE
            if is_regex:
                content_regex = re.compile(search_content, flags)
            else:
                content_regex = re.compile(re.escape(search_content), flags)

        iterator = target_dir.rglob(glob_pat) if recursive else target_dir.glob(glob_pat)

        for file_path in iterator:
            if len(results) >= max_results:
                break

            if not file_path.is_file():
                continue

            # Check if any parent part matches ignored dirs
            try:
                rel_parts = file_path.relative_to(target_dir).parts
            except ValueError:
                continue

            if any(part in DEFAULT_IGNORED_DIRS for part in rel_parts[:-1]):
                continue

            if not include_hidden and any(part.startswith(".") for part in rel_parts):
                continue

            rel_str = self.security.get_relative_path(file_path)

            # If no content search was requested, match is on filename
            if not content_regex:
                results.append(SearchResultItem(path=rel_str))
                continue

            # Content search: skip binary files
            if FileReaderTool.is_binary_file(file_path):
                continue

            # Scan lines
            try:
                with open(file_path, "r", encoding=encoding, errors="replace") as f:
                    for line_idx, line in enumerate(f, start=1):
                        match = content_regex.search(line)
                        if match:
                            results.append(
                                SearchResultItem(
                                    path=rel_str,
                                    line_number=line_idx,
                                    line_content=line.rstrip("\r\n"),
                                    match_start=match.start(),
                                    match_end=match.end(),
                                )
                            )
                            if len(results) >= max_results:
                                break
            except Exception as err:
                logger.debug("Failed scanning content for '%s': %s", file_path, err)
                continue

        return results


__all__ = ["FileSearchTool"]
