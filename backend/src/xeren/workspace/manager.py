"""Central WorkspaceManager orchestrating permissions, scanning, search, ranking, and retrieval.

Provides a unified, secure boundary through which Xeren Core, Planners, and Autonomous Agents
interact with authorized workspace environments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from xeren.workspace.content import WorkspaceContentRetriever
from xeren.workspace.permissions import (
    PathTraversalError,
    SecurityViolationError,
    UnauthorizedRootError,
    WorkspacePermissionError,
    WorkspacePermissionManager,
    WorkspaceSecurityError,
)
from xeren.workspace.relevance import RelevanceRanker
from xeren.workspace.scanner import WorkspaceScanner
from xeren.workspace.schemas import (
    CandidateFile,
    DiscoveryRequest,
    DiscoveryResult,
    PermissionMode,
    RetrievedContent,
    ScannedFileMetadata,
    WorkspaceContext,
    WorkspaceRequirement,
    WorkspaceRoot,
)
from xeren.workspace.search import WorkspaceSearchIndex

logger = logging.getLogger("xeren.workspace.manager")


class WorkspaceManager:
    """The central coordinator for Xeren Workspace & File Intelligence.

    Guarantees:
    - Zero direct LLM filesystem access.
    - Strict confinement to authorized roots.
    - Default READ_ONLY permissions.
    - Fast metadata discovery without full-file overhead.
    - Multi-signal ranking and safe ambiguity handling.
    - Seamless reuse of existing RAG without duplicate pipelines.
    """

    def __init__(
        self,
        permission_manager: Optional[WorkspacePermissionManager] = None,
        scanner: Optional[WorkspaceScanner] = None,
        search_index: Optional[WorkspaceSearchIndex] = None,
        ranker: Optional[RelevanceRanker] = None,
        content_retriever: Optional[WorkspaceContentRetriever] = None,
    ) -> None:
        self.permissions = permission_manager or WorkspacePermissionManager()
        self.scanner = scanner or WorkspaceScanner(permission_manager=self.permissions)
        self.search_index = search_index or WorkspaceSearchIndex()
        self.ranker = ranker or RelevanceRanker()
        self.content_retriever = content_retriever or WorkspaceContentRetriever(
            permission_manager=self.permissions
        )
        self._last_context: Optional[WorkspaceContext] = None

    # -------------------------------------------------------------------------
    # Root Authorization Lifecycle
    # -------------------------------------------------------------------------
    def authorize_root(
        self,
        path: Union[str, Path],
        root_id: Optional[str] = None,
        permission_mode: Optional[PermissionMode] = None,
        allowed_operations: Optional[List[str]] = None,
    ) -> WorkspaceRoot:
        """Explicitly authorize a filesystem directory as a workspace root."""
        root = self.permissions.authorize_root(
            path=path,
            root_id=root_id,
            permission_mode=permission_mode,
            allowed_operations=allowed_operations,
        )
        # Scan and index new root
        self.scan(root_id=root.root_id)
        return root

    def add_root(self, root: WorkspaceRoot) -> None:
        """Register an existing WorkspaceRoot."""
        self.permissions.add_root(root)
        self.scan(root_id=root.root_id)

    def remove_root(self, root_id: str) -> Optional[WorkspaceRoot]:
        """Remove a root and clear its indexed files."""
        removed = self.permissions.remove_root(root_id)
        if removed:
            self.scanner.invalidate_cache(root_id=root_id)
            # Reindex remaining roots
            self.search_index.clear()
            self.scan()
        return removed

    def get_root(self, root_id: str) -> WorkspaceRoot:
        """Get an authorized root by ID."""
        return self.permissions.get_root(root_id)

    def list_roots(self, active_only: bool = True) -> List[WorkspaceRoot]:
        """List authorized roots."""
        return self.permissions.list_roots(active_only=active_only)

    # -------------------------------------------------------------------------
    # Scanning and Indexing
    # -------------------------------------------------------------------------
    def scan(
        self,
        root_id: Optional[str] = None,
        force_rescan: bool = False,
    ) -> List[ScannedFileMetadata]:
        """Lightweight metadata scan over specified root or all authorized roots."""
        if root_id:
            root = self.permissions.get_root(root_id)
            scanned = self.scanner.scan_root(root, force_rescan=force_rescan)
        else:
            scanned = self.scanner.scan_all(force_rescan=force_rescan)

        self.search_index.index_files(scanned)
        logger.info("Scanned and indexed %d files across workspace roots", len(scanned))
        return scanned

    # -------------------------------------------------------------------------
    # Autonomous File Discovery & Ranking
    # -------------------------------------------------------------------------
    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Discover and rank candidate workspace files relevant to a user task.

        Step 1: Fetch candidate pool via search index or full scanned files.
        Step 2: Score candidates through multi-signal RelevanceRanker.
        Step 3: Evaluate ambiguity (auto-select vs ask user vs no-match).
        """
        # Ensure roots are scanned
        all_indexed = self.search_index.get_all()
        if not all_indexed:
            all_indexed = self.scan()

        if not all_indexed:
            clarification = (
                f"No files available in the authorized workspace to fulfill: '{request.goal}'."
            )
            return DiscoveryResult(
                candidates=[],
                selected_candidates=[],
                ambiguity_detected=False,
                clarification_message=clarification,
                total_files_scanned=0,
            )

        # Filter candidate pool
        candidate_pool = self.search_index.search(
            query=request.goal,
            search_terms=request.search_terms,
            preferred_types=request.preferred_types,
            root_id=request.workspace_root_id,
        )

        # If query filtering was too strict, fallback to broader root files
        if not candidate_pool:
            if request.workspace_root_id:
                candidate_pool = [
                    f for f in all_indexed if f.root_id == request.workspace_root_id
                ]
            else:
                candidate_pool = all_indexed

        # Rank candidates
        result = self.ranker.rank_candidates(
            goal=request.goal,
            files=candidate_pool,
            preferred_types=request.preferred_types,
            task_context=request.task_context,
            min_score_threshold=request.min_score_threshold,
            max_candidates=request.max_candidates,
        )

        return result

    # -------------------------------------------------------------------------
    # Content Retrieval
    # -------------------------------------------------------------------------
    def retrieve(
        self,
        candidate: CandidateFile,
        max_preview_lines: int = 100,
        chunk_content: bool = True,
    ) -> RetrievedContent:
        """Retrieve and sanitize content for a selected candidate file."""
        return self.content_retriever.retrieve(
            candidate=candidate,
            max_preview_lines=max_preview_lines,
            chunk_content=chunk_content,
        )

    # -------------------------------------------------------------------------
    # Structured Workspace Context Builder
    # -------------------------------------------------------------------------
    def build_context(
        self,
        goal: str,
        requirement: Optional[WorkspaceRequirement] = None,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceContext:
        """Build high-level structured WorkspaceContext for Core and Autonomous Agent."""
        req = requirement or WorkspaceRequirement(
            purpose="task_resource_discovery",
            query_terms=[goal],
        )

        preferred = req.preferred_types if req.preferred_types else None

        discovery_req = DiscoveryRequest(
            goal=goal,
            task_context=task_context,
            preferred_types=preferred,
            search_terms=req.query_terms,
        )

        discovery_res = self.discover(discovery_req)

        # Retrieve content for selected candidate(s)
        retrieval_status: Dict[str, str] = {}
        for selected in discovery_res.selected_candidates:
            try:
                retrieved = self.retrieve(selected)
                retrieval_status[selected.relative_path] = (
                    "retrieved_text" if not retrieved.is_binary else "retrieved_binary_metadata"
                )
            except Exception as err:
                retrieval_status[selected.relative_path] = f"error: {err}"

        roots = self.permissions.list_roots(active_only=True)
        perms = {r.root_id: r.permission_mode for r in roots}

        ctx = WorkspaceContext(
            authorized_roots=roots,
            discovered_candidates=discovery_res.candidates,
            selected_resources=discovery_res.selected_candidates,
            retrieval_status=retrieval_status,
            permissions=perms,
            task_relationship=f"Discovered resources for goal: '{goal}'",
            ambiguity_detected=discovery_res.ambiguity_detected,
            clarification_message=discovery_res.clarification_message,
        )

        self._last_context = ctx
        return ctx

    # -------------------------------------------------------------------------
    # RAG Integration (Reusing existing RAG pipeline without duplication)
    # -------------------------------------------------------------------------
    def ingest_into_rag(
        self,
        candidate: CandidateFile,
        rag_pipeline_or_knowledge: Any,
    ) -> List[str]:
        """Ingest a discovered workspace file into the existing Xeren RAG system."""
        path = candidate.absolute_path

        # Case 1: IngestionPipeline instance
        if hasattr(rag_pipeline_or_knowledge, "process_file") and hasattr(rag_pipeline_or_knowledge, "index_chunks"):
            chunks = rag_pipeline_or_knowledge.process_file(path)
            if hasattr(rag_pipeline_or_knowledge, "vector_store") and rag_pipeline_or_knowledge.vector_store:
                return rag_pipeline_or_knowledge.index_chunks(chunks)
            return [c.chunk_id for c in chunks]

        # Case 2: KnowledgePlugin instance
        if hasattr(rag_pipeline_or_knowledge, "ingest"):
            from xeren.rag.document import Document
            retrieved = self.retrieve(candidate)
            doc = Document.from_text(
                text=retrieved.content or "",
                source=str(path),
                title=candidate.relative_path,
            )
            rag_pipeline_or_knowledge.ingest(documents=[doc])
            return [doc.id]

        raise TypeError(
            f"Unsupported RAG object type '{type(rag_pipeline_or_knowledge).__name__}'. "
            "Expected IngestionPipeline or KnowledgePlugin."
        )

    # -------------------------------------------------------------------------
    # Safe Modifying Operations (Guarded by READ_WRITE permissions)
    # -------------------------------------------------------------------------
    def write_file(
        self,
        raw_path: Union[str, Path],
        content: str,
        root_id: Optional[str] = None,
        overwrite: bool = True,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Write content to an authorized workspace path strictly enforcing READ_WRITE permission."""
        resolved_path, root = self.permissions.validate_path(
            raw_path=raw_path,
            root_id=root_id,
            operation="write",
            must_exist=False,
        )

        if resolved_path.exists() and not overwrite:
            raise FileExistsError(f"Target file '{raw_path}' already exists and overwrite is False")

        # Create parent directories safely
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        with open(resolved_path, "w", encoding=encoding) as f:
            f.write(content)

        rel_path = self.permissions.get_relative_path(resolved_path, root)
        # Update scanner index incrementally
        self.scan(root_id=root.root_id)

        return {
            "success": True,
            "path": rel_path,
            "bytes_written": len(content.encode(encoding)),
            "root_id": root.root_id,
        }


__all__ = [
    "WorkspaceManager",
    "WorkspaceSecurityError",
    "PathTraversalError",
    "UnauthorizedRootError",
    "WorkspacePermissionError",
    "SecurityViolationError",
]
