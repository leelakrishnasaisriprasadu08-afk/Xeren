"""Workspace search index providing fast token matching, pattern matching, and metadata filtering.

Maintains an in-memory index of scanned files for instantaneous candidate discovery
without re-traversing the filesystem.
"""

from __future__ import annotations

from fnmatch import fnmatch
import logging
import re
from typing import Dict, List, Optional, Sequence, Set

from xeren.workspace.schemas import FileCategory, ScannedFileMetadata

logger = logging.getLogger("xeren.workspace.search")

# Regex to tokenize filenames and paths into searchable terms
TOKEN_SPLIT_REGEX = re.compile(r"[^a-zA-Z0-9]+")


def tokenize(text: str) -> Set[str]:
    """Extract normalized alphanumeric tokens from text."""
    parts = TOKEN_SPLIT_REGEX.split(text.lower())
    return {p for p in parts if len(p) >= 2}


class WorkspaceSearchIndex:
    """Fast, lightweight search index over scanned workspace files."""

    def __init__(self) -> None:
        # file_id -> ScannedFileMetadata
        self._files: Dict[str, ScannedFileMetadata] = {}
        # token -> set of file_ids
        self._inverted_index: Dict[str, Set[str]] = {}
        # extension -> set of file_ids
        self._ext_index: Dict[str, Set[str]] = {}
        # category -> set of file_ids
        self._category_index: Dict[FileCategory, Set[str]] = {}
        # root_id -> set of file_ids
        self._root_index: Dict[str, Set[str]] = {}

    def index_files(self, metadata_list: Sequence[ScannedFileMetadata]) -> None:
        """Bulk index or refresh a collection of scanned files."""
        for meta in metadata_list:
            self.add_or_update(meta)

    def add_or_update(self, meta: ScannedFileMetadata) -> None:
        """Add or update a single file's metadata in the index."""
        # Remove old index entries if updating
        if meta.file_id in self._files:
            self.remove(meta.file_id)

        self._files[meta.file_id] = meta

        # 1. Index tokens from filename, stem, and relative path parts
        tokens = tokenize(meta.name) | tokenize(meta.relative_path)
        for token in tokens:
            if token not in self._inverted_index:
                self._inverted_index[token] = set()
            self._inverted_index[token].add(meta.file_id)

        # 2. Index extension
        ext = meta.extension.lower().lstrip(".")
        if ext:
            if ext not in self._ext_index:
                self._ext_index[ext] = set()
            self._ext_index[ext].add(meta.file_id)

        # 3. Index category
        if meta.category not in self._category_index:
            self._category_index[meta.category] = set()
        self._category_index[meta.category].add(meta.file_id)

        # 4. Index root
        if meta.root_id not in self._root_index:
            self._root_index[meta.root_id] = set()
        self._root_index[meta.root_id].add(meta.file_id)

    def remove(self, file_id: str) -> None:
        """Remove a file from the index."""
        meta = self._files.pop(file_id, None)
        if not meta:
            return

        tokens = tokenize(meta.name) | tokenize(meta.relative_path)
        for token in tokens:
            if token in self._inverted_index:
                self._inverted_index[token].discard(file_id)
                if not self._inverted_index[token]:
                    del self._inverted_index[token]

        ext = meta.extension.lower().lstrip(".")
        if ext in self._ext_index:
            self._ext_index[ext].discard(file_id)

        if meta.category in self._category_index:
            self._category_index[meta.category].discard(file_id)

        if meta.root_id in self._root_index:
            self._root_index[meta.root_id].discard(file_id)

    def search(
        self,
        query: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        preferred_types: Optional[List[str]] = None,
        categories: Optional[List[FileCategory]] = None,
        root_id: Optional[str] = None,
        glob_pattern: Optional[str] = None,
    ) -> List[ScannedFileMetadata]:
        """Search indexed files matching query terms, extensions, and filters."""
        # Start with root-filtered or all candidate file IDs
        if root_id:
            candidate_ids: Set[str] = set(self._root_index.get(root_id, set()))
        else:
            candidate_ids = set(self._files.keys())

        if not candidate_ids:
            return []

        # Filter by category if requested
        if categories:
            cat_ids: Set[str] = set()
            for cat in categories:
                cat_ids.update(self._category_index.get(cat, set()))
            candidate_ids &= cat_ids

        # Filter by preferred extensions if requested
        if preferred_types:
            norm_types = {t.lower().lstrip(".") for t in preferred_types}
            ext_ids: Set[str] = set()
            for ext in norm_types:
                ext_ids.update(self._ext_index.get(ext, set()))
            candidate_ids &= ext_ids

        if not candidate_ids:
            return []

        # Filter by glob pattern if provided
        if glob_pattern:
            candidate_ids = {
                fid for fid in candidate_ids
                if fnmatch(self._files[fid].name.lower(), glob_pattern.lower())
                or fnmatch(self._files[fid].relative_path.lower(), glob_pattern.lower())
            }

        # Filter / score by query terms
        all_terms: List[str] = []
        if search_terms:
            all_terms.extend([t.lower() for t in search_terms])
        if query:
            all_terms.extend(list(tokenize(query)))

        if not all_terms:
            return [self._files[fid] for fid in candidate_ids]

        # Score candidate files based on token matches
        results: List[ScannedFileMetadata] = []
        for fid in candidate_ids:
            file_meta = self._files[fid]
            file_tokens = tokenize(file_meta.name) | tokenize(file_meta.relative_path)

            # Match if any term matches tokens or is substring of name/path
            matched = False
            for term in all_terms:
                if term in file_tokens or term in file_meta.name.lower() or term in file_meta.relative_path.lower():
                    matched = True
                    break

            if matched:
                results.append(file_meta)

        return results

    def get_all(self) -> List[ScannedFileMetadata]:
        """Retrieve all currently indexed file metadata."""
        return list(self._files.values())

    def clear(self) -> None:
        """Clear all indexed data."""
        self._files.clear()
        self._inverted_index.clear()
        self._ext_index.clear()
        self._category_index.clear()
        self._root_index.clear()


__all__ = ["WorkspaceSearchIndex", "tokenize"]
