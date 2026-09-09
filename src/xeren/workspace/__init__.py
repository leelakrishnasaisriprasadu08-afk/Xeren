"""Xeren Workspace & File Intelligence Subsystem.

Provides autonomous, task-driven workspace file discovery, relevance ranking,
strict security boundary enforcement, lightweight metadata scanning, and safe
content retrieval for Xeren Core, Planners, and Autonomous Agents.
"""

from xeren.workspace.content import WorkspaceContentRetriever
from xeren.workspace.manager import WorkspaceManager
from xeren.workspace.permissions import (
    DANGEROUS_EXECUTABLE_EXTS,
    RESTRICTED_DIRECTORIES,
    WINDOWS_RESERVED_NAMES,
    PathTraversalError,
    SecurityViolationError,
    UnauthorizedRootError,
    WorkspacePermissionError,
    WorkspacePermissionManager,
    WorkspaceSecurityError,
)
from xeren.workspace.relevance import (
    CODE_KEYWORDS,
    DATA_KEYWORDS,
    DOC_KEYWORDS,
    RECENCY_KEYWORDS,
    RelevanceRanker,
)
from xeren.workspace.scanner import (
    CATEGORY_MAP,
    WorkspaceScanner,
    infer_file_category,
)
from xeren.workspace.schemas import (
    CandidateFile,
    DiscoveryRequest,
    DiscoveryResult,
    FileCategory,
    PermissionMode,
    RetrievedContent,
    ScannedFileMetadata,
    WorkspaceContext,
    WorkspaceRequirement,
    WorkspaceRoot,
)
from xeren.workspace.search import WorkspaceSearchIndex, tokenize

__all__ = [
    # Core Manager
    "WorkspaceManager",
    # Security & Permissions
    "WorkspacePermissionManager",
    "WorkspaceSecurityError",
    "PathTraversalError",
    "UnauthorizedRootError",
    "WorkspacePermissionError",
    "SecurityViolationError",
    "WINDOWS_RESERVED_NAMES",
    "DANGEROUS_EXECUTABLE_EXTS",
    "RESTRICTED_DIRECTORIES",
    # Scanner
    "WorkspaceScanner",
    "infer_file_category",
    "CATEGORY_MAP",
    # Search Index
    "WorkspaceSearchIndex",
    "tokenize",
    # Relevance & Ambiguity
    "RelevanceRanker",
    "DATA_KEYWORDS",
    "DOC_KEYWORDS",
    "CODE_KEYWORDS",
    "RECENCY_KEYWORDS",
    # Content Retrieval
    "WorkspaceContentRetriever",
    # Schemas
    "PermissionMode",
    "FileCategory",
    "WorkspaceRoot",
    "ScannedFileMetadata",
    "WorkspaceRequirement",
    "DiscoveryRequest",
    "CandidateFile",
    "DiscoveryResult",
    "RetrievedContent",
    "WorkspaceContext",
]
