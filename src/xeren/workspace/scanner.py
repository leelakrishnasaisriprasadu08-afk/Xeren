"""Workspace scanner for fast, lightweight metadata discovery without loading file contents.

Traverses authorized workspace roots and collects structural metadata (file paths,
extensions, sizes, mtimes, MIME types, and categories) while ignoring noise directories
and respecting workspace security boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.schemas import (
    FileCategory,
    ScannedFileMetadata,
    WorkspaceRoot,
)

logger = logging.getLogger("xeren.workspace.scanner")

# Map file extensions to primary semantic categories
CATEGORY_MAP: Dict[str, FileCategory] = {
    # Structured data
    ".csv": FileCategory.STRUCTURED_DATA,
    ".tsv": FileCategory.STRUCTURED_DATA,
    ".xlsx": FileCategory.STRUCTURED_DATA,
    ".xls": FileCategory.STRUCTURED_DATA,
    ".parquet": FileCategory.STRUCTURED_DATA,
    ".feather": FileCategory.STRUCTURED_DATA,
    ".ndjson": FileCategory.STRUCTURED_DATA,
    ".jsonl": FileCategory.STRUCTURED_DATA,
    # Documents
    ".pdf": FileCategory.DOCUMENT,
    ".docx": FileCategory.DOCUMENT,
    ".doc": FileCategory.DOCUMENT,
    ".md": FileCategory.DOCUMENT,
    ".markdown": FileCategory.DOCUMENT,
    ".txt": FileCategory.DOCUMENT,
    ".rst": FileCategory.DOCUMENT,
    ".rtf": FileCategory.DOCUMENT,
    # Source code
    ".py": FileCategory.SOURCE_CODE,
    ".ts": FileCategory.SOURCE_CODE,
    ".tsx": FileCategory.SOURCE_CODE,
    ".js": FileCategory.SOURCE_CODE,
    ".jsx": FileCategory.SOURCE_CODE,
    ".go": FileCategory.SOURCE_CODE,
    ".rs": FileCategory.SOURCE_CODE,
    ".java": FileCategory.SOURCE_CODE,
    ".c": FileCategory.SOURCE_CODE,
    ".cpp": FileCategory.SOURCE_CODE,
    ".h": FileCategory.SOURCE_CODE,
    ".hpp": FileCategory.SOURCE_CODE,
    ".cs": FileCategory.SOURCE_CODE,
    ".rb": FileCategory.SOURCE_CODE,
    ".php": FileCategory.SOURCE_CODE,
    ".sql": FileCategory.SOURCE_CODE,
    ".html": FileCategory.SOURCE_CODE,
    ".css": FileCategory.SOURCE_CODE,
    # Config
    ".yaml": FileCategory.CONFIG,
    ".yml": FileCategory.CONFIG,
    ".toml": FileCategory.CONFIG,
    ".ini": FileCategory.CONFIG,
    ".cfg": FileCategory.CONFIG,
    ".conf": FileCategory.CONFIG,
    # Archives
    ".zip": FileCategory.ARCHIVE,
    ".tar": FileCategory.ARCHIVE,
    ".gz": FileCategory.ARCHIVE,
    ".7z": FileCategory.ARCHIVE,
    # Binary media
    ".png": FileCategory.BINARY,
    ".jpg": FileCategory.BINARY,
    ".jpeg": FileCategory.BINARY,
    ".gif": FileCategory.BINARY,
    ".webp": FileCategory.BINARY,
    ".ico": FileCategory.BINARY,
    ".db": FileCategory.BINARY,
    ".sqlite": FileCategory.BINARY,
}

TEXT_EXTENSIONS = frozenset([
    ".csv", ".tsv", ".txt", ".md", ".markdown", ".rst", ".json", ".ndjson", ".jsonl",
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h",
    ".hpp", ".cs", ".rb", ".php", ".sh", ".sql", ".html", ".css", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".xml"
])


def infer_file_category(name: str, ext: str, is_dir: bool) -> FileCategory:
    """Infer file category using extension, name heuristics, and directory status."""
    if is_dir:
        return FileCategory.UNKNOWN

    low_ext = ext.lower()
    if low_ext in CATEGORY_MAP:
        return CATEGORY_MAP[low_ext]

    # Special handling for JSON: might be structured data or config
    if low_ext == ".json":
        low_name = name.lower()
        if any(k in low_name for k in ("data", "report", "records", "sales", "metrics", "stats")):
            return FileCategory.STRUCTURED_DATA
        return FileCategory.CONFIG

    return FileCategory.UNKNOWN


class WorkspaceScanner:
    """Scans authorized workspace roots and builds lightweight file metadata."""

    def __init__(
        self,
        permission_manager: Optional[WorkspacePermissionManager] = None,
        max_scan_depth: int = 15,
        max_files_per_root: int = 5000,
    ) -> None:
        self.permissions = permission_manager or WorkspacePermissionManager()
        self.max_scan_depth = max_scan_depth
        self.max_files_per_root = max_files_per_root
        # Cache indexed by (root_id, relative_path) -> ScannedFileMetadata
        self._cache: Dict[str, ScannedFileMetadata] = {}

    def scan_root(
        self,
        root: WorkspaceRoot,
        force_rescan: bool = False,
    ) -> List[ScannedFileMetadata]:
        """Scan a single authorized workspace root and return metadata for all valid files."""
        if not root.enabled or not root.can_read():
            logger.warning("Skipping scan on disabled or non-readable root: %s", root.root_id)
            return []

        root_path = root.path.resolve()
        if not root_path.exists() or not root_path.is_dir():
            logger.warning("Root path does not exist or is not a directory: %s", root_path)
            return []

        results: List[ScannedFileMetadata] = []
        files_count = 0

        for current_dir, dirs, files in os.walk(root_path, topdown=True):
            if files_count >= self.max_files_per_root:
                logger.info("Reached maximum file limit (%d) for root '%s'", self.max_files_per_root, root.root_id)
                break

            cur_p = Path(current_dir)

            # Filter dirs in-place to prevent traversing noise and restricted directories
            dirs[:] = [
                d for d in dirs
                if self.permissions.is_safe_for_scanning(cur_p / d, root)
            ]

            # Process files in current_dir
            for fname in files:
                if files_count >= self.max_files_per_root:
                    break

                file_path = cur_p / fname
                if not self.permissions.is_safe_for_scanning(file_path, root):
                    continue

                try:
                    rel_path = self.permissions.get_relative_path(file_path, root)
                    cache_key = f"{root.root_id}:{rel_path}"

                    stat = file_path.stat()
                    mtime_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

                    # Check cache freshness
                    if not force_rescan and cache_key in self._cache:
                        cached = self._cache[cache_key]
                        if cached.modified_at == mtime_dt and cached.size_bytes == stat.st_size:
                            results.append(cached)
                            files_count += 1
                            continue

                    ctime_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
                    ext = file_path.suffix.lower()
                    mime_type, _ = mimetypes.guess_type(fname)
                    category = infer_file_category(fname, ext, is_dir=False)

                    # Binary heuristic: text extensions are never binary
                    if ext in TEXT_EXTENSIONS:
                        is_binary = False
                    else:
                        is_binary = (
                            category in (FileCategory.BINARY, FileCategory.ARCHIVE)
                            or (mime_type is not None and not mime_type.startswith("text/") and mime_type not in ("application/json", "application/javascript"))
                        )

                    meta = ScannedFileMetadata(
                        file_id=f"{root.root_id}:{rel_path}",
                        name=fname,
                        relative_path=rel_path,
                        absolute_path=file_path.resolve(),
                        extension=ext,
                        size_bytes=stat.st_size,
                        created_at=ctime_dt,
                        modified_at=mtime_dt,
                        mime_type=mime_type,
                        is_binary=is_binary,
                        is_directory=False,
                        category=category,
                        root_id=root.root_id,
                    )

                    self._cache[cache_key] = meta
                    results.append(meta)
                    files_count += 1

                except (OSError, PermissionError) as err:
                    logger.debug("Skipping inaccessible file '%s': %s", file_path, err)
                    continue

        return results

    def scan_all(self, force_rescan: bool = False) -> List[ScannedFileMetadata]:
        """Scan all authorized and enabled workspace roots."""
        all_metadata: List[ScannedFileMetadata] = []
        for root in self.permissions.list_roots(active_only=True):
            all_metadata.extend(self.scan_root(root, force_rescan=force_rescan))
        return all_metadata

    def get_cached_metadata(self, root_id: str, relative_path: str) -> Optional[ScannedFileMetadata]:
        """Lookup previously scanned metadata from cache."""
        return self._cache.get(f"{root_id}:{relative_path}")

    def invalidate_cache(self, root_id: Optional[str] = None) -> None:
        """Invalidate scanner cache."""
        if root_id:
            prefix = f"{root_id}:"
            self._cache = {k: v for k, v in self._cache.items() if not k.startswith(prefix)}
        else:
            self._cache.clear()


__all__ = [
    "WorkspaceScanner",
    "infer_file_category",
    "CATEGORY_MAP",
]
