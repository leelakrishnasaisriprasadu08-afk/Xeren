"""Pydantic schemas for Xeren Plugin #6: File Plugin."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileOperation(str, Enum):
    """Supported operations for the Xeren File Plugin."""

    READ = "read"
    WRITE = "write"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    LIST = "list"
    SEARCH = "search"
    MOVE = "move"
    COPY = "copy"
    METADATA = "metadata"


class FileItemMetadata(BaseModel):
    """Detailed metadata representing a filesystem entity (file or directory)."""

    path: str = Field(..., description="Relative path within the workspace")
    name: str = Field(..., description="Base filename or directory name")
    size_bytes: int = Field(default=0, ge=0, description="Size in bytes")
    is_directory: bool = Field(default=False, description="Whether the path points to a directory")
    is_file: bool = Field(default=False, description="Whether the path points to a regular file")
    is_symlink: bool = Field(default=False, description="Whether the path is a symbolic link")
    extension: str = Field(default="", description="File extension including leading dot (e.g. .py)")
    mime_type: Optional[str] = Field(default=None, description="Inferred MIME type if available")
    is_binary: bool = Field(default=False, description="Whether the file contains non-text/binary data")
    created_at: Optional[datetime] = Field(default=None, description="Entity creation timestamp")
    modified_at: Optional[datetime] = Field(default=None, description="Entity modification timestamp")
    permissions: Optional[str] = Field(default=None, description="Octal or string representation of file permissions")
    checksum_sha256: Optional[str] = Field(default=None, description="SHA-256 digest of file content")


class SearchResultItem(BaseModel):
    """A matched item or line match from a file search operation."""

    path: str = Field(..., description="Relative path of the matching file")
    line_number: Optional[int] = Field(default=None, ge=1, description="1-indexed line number if content matched")
    line_content: Optional[str] = Field(default=None, description="Matching line content snippet")
    match_start: Optional[int] = Field(default=None, ge=0, description="Start character offset of match in line")
    match_end: Optional[int] = Field(default=None, ge=0, description="End character offset of match in line")


class FileInput(BaseModel):
    """Input payload for File Plugin operations."""

    operation: FileOperation = Field(default=FileOperation.READ, description="Filesystem operation to perform")
    path: Optional[str] = Field(default=None, description="Primary relative file or directory path within workspace")
    destination_path: Optional[str] = Field(default=None, description="Destination path for move/copy operations")
    content: Optional[str] = Field(default=None, description="File text content for write/create/modify operations")
    encoding: str = Field(default="utf-8", description="Character encoding for text operations")
    pattern: Optional[str] = Field(default=None, description="Glob pattern for listing or searching files")
    search_content: Optional[str] = Field(default=None, description="Text or regex pattern to search inside file contents")
    is_regex: bool = Field(default=False, description="Whether search_content is evaluated as a regular expression")
    case_sensitive: bool = Field(default=True, description="Whether search is case-sensitive")
    recursive: bool = Field(default=True, description="Whether directory listing or search traverses recursively")
    include_hidden: bool = Field(default=False, description="Whether to include hidden dotfiles in listing or search")
    max_results: int = Field(default=100, ge=1, le=10000, description="Maximum number of items or matches to return")
    max_size_bytes: Optional[int] = Field(default=None, gt=0, description="Maximum allowed file size limit in bytes")
    atomic: bool = Field(default=True, description="Whether to perform writes atomically via temporary file replacement")
    create_parents: bool = Field(default=True, description="Whether to automatically create intermediate parent directories")
    overwrite: bool = Field(default=False, description="Whether existing files may be overwritten")
    dry_run: bool = Field(default=False, description="Simulate the operation and return what would happen without modifying filesystem")
    redaction_enabled: bool = Field(default=True, description="Whether to perform best-effort secret redaction on output content")
    line_start: Optional[int] = Field(default=None, ge=1, description="1-indexed starting line number for partial reading or editing")
    line_end: Optional[int] = Field(default=None, ge=1, description="1-indexed ending line number for partial reading or editing")
    target_content: Optional[str] = Field(default=None, description="Target substring or block to replace during modify")
    replacement: Optional[str] = Field(default=None, description="Replacement text for modify operation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata or flags")


class FileResult(BaseModel):
    """Standardized output structure for File Plugin operations."""

    operation: FileOperation = Field(..., description="Operation performed")
    success: bool = Field(..., description="Whether the operation succeeded")
    path: Optional[str] = Field(default=None, description="Target path affected by the operation")
    destination_path: Optional[str] = Field(default=None, description="Destination path for move/copy operations")
    content: Optional[str] = Field(default=None, description="Text content retrieved during read operations")
    items: List[FileItemMetadata] = Field(default_factory=list, description="Directory listing results")
    search_results: List[SearchResultItem] = Field(default_factory=list, description="Search matches")
    metadata: Optional[FileItemMetadata] = Field(default=None, description="File metadata details if requested")
    bytes_written: Optional[int] = Field(default=None, ge=0, description="Bytes written during write/modify")
    bytes_read: Optional[int] = Field(default=None, ge=0, description="Bytes read during read operations")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    warning: Optional[str] = Field(default=None, description="Warning message (e.g. binary file detected, partial read)")
    dry_run: bool = Field(default=False, description="Indicates whether the result is from a simulated dry run")
    redacted_secrets: bool = Field(default=False, description="Indicates whether best-effort secret redaction occurred")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Performance and diagnostic metrics")


__all__ = [
    "FileOperation",
    "FileItemMetadata",
    "SearchResultItem",
    "FileInput",
    "FileResult",
]
