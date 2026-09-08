"""Relevance ranking and ambiguity evaluation engine for Xeren Workspace Intelligence.

Ranks candidates using multi-signal scoring:
1. Filename match & token overlap.
2. Path hierarchy relevance (e.g. data/, docs/, src/auth/).
3. Extension and category alignment with user task.
4. Temporal recency (e.g. "yesterday", "recent" queries).
5. Safe peek at text header lines for domain confirmation.
6. Ambiguity detection (auto-selection vs. user clarification vs. safe no-match notice).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from xeren.workspace.schemas import (
    CandidateFile,
    DiscoveryResult,
    FileCategory,
    ScannedFileMetadata,
)
from xeren.workspace.search import tokenize

logger = logging.getLogger("xeren.workspace.relevance")

# Task intent patterns
DATA_KEYWORDS = {"sales", "revenue", "data", "dataset", "csv", "excel", "sheet", "metric", "metrics", "trend", "analytics", "churn", "finance", "kpi"}
DOC_KEYWORDS = {"research", "paper", "papers", "document", "documents", "spec", "specification", "requirements", "report", "notes", "article", "thesis"}
CODE_KEYWORDS = {"code", "project", "bug", "fix", "auth", "login", "endpoint", "api", "function", "refactor", "tests", "implementation", "script", "controller"}
WEBSITE_KEYWORDS = {"website", "web", "dashboard", "frontend", "html", "page", "ui", "landing"}

# Domain synonyms
AUTH_SYNONYMS = {"auth", "login", "authenticate", "authentication", "signin", "signup", "user", "session", "password", "credential"}
SALES_SYNONYMS = {"sales", "revenue", "orders", "invoices", "dataset", "data", "metrics", "financial"}

# Temporal trigger terms
RECENCY_KEYWORDS = {"yesterday", "recent", "recently", "latest", "today", "current", "newest"}

# Multi-file intent triggers
MULTI_FILE_TRIGGERS = {"papers", "documents", "files", "datasets", "both", "all", "requirements and", "and project", "together"}


class RelevanceRanker:
    """Computes multi-signal relevance scores and resolves ambiguity."""

    def __init__(
        self,
        auto_select_threshold: float = 0.65,
        ambiguity_margin: float = 0.08,
        min_score_threshold: float = 0.35,
    ) -> None:
        self.auto_select_threshold = auto_select_threshold
        self.ambiguity_margin = ambiguity_margin
        self.min_score_threshold = min_score_threshold

    def rank_candidates(
        self,
        goal: str,
        files: Sequence[ScannedFileMetadata],
        preferred_types: Optional[List[str]] = None,
        task_context: Optional[Dict[str, Any]] = None,
        min_score_threshold: Optional[float] = None,
        max_candidates: int = 10,
    ) -> DiscoveryResult:
        """Score and rank files for a given goal, producing a structured DiscoveryResult."""
        start_time = datetime.now(timezone.utc)
        min_score = min_score_threshold if min_score_threshold is not None else self.min_score_threshold

        goal_lower = goal.lower()
        goal_tokens = tokenize(goal)

        norm_preferred_types: Optional[Set[str]] = (
            {t.lower().lstrip(".") for t in preferred_types}
            if preferred_types
            else None
        )

        recency_focus = any(kw in goal_lower for kw in RECENCY_KEYWORDS)

        scored_candidates: List[CandidateFile] = []

        for f in files:
            score, reason = self.score_file(
                goal=goal,
                goal_tokens=goal_tokens,
                file_meta=f,
                preferred_types=norm_preferred_types,
                recency_focus=recency_focus,
            )

            if score >= min_score:
                ext_clean = f.extension.lstrip(".").lower() or "file"
                cand = CandidateFile(
                    file_id=f.file_id,
                    relative_path=f.relative_path,
                    absolute_path=f.absolute_path,
                    file_type=ext_clean,
                    score=round(score, 3),
                    reason=reason,
                    metadata={
                        "size_bytes": f.size_bytes,
                        "category": f.category.value,
                        "modified_at": f.modified_at.isoformat(),
                        "mime_type": f.mime_type,
                    },
                    scanned_meta=f,
                )
                scored_candidates.append(cand)

        # Sort descending by score, then recency
        scored_candidates.sort(
            key=lambda c: (
                c.score,
                c.scanned_meta.modified_at.timestamp() if c.scanned_meta else 0.0,
            ),
            reverse=True,
        )

        top_candidates = scored_candidates[:max_candidates]

        # Evaluate ambiguity / selection
        selected, is_ambiguous, clarification = self.evaluate_ambiguity(top_candidates, goal)

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0

        return DiscoveryResult(
            candidates=top_candidates,
            selected_candidates=selected,
            ambiguity_detected=is_ambiguous,
            clarification_message=clarification,
            total_files_scanned=len(files),
            duration_ms=round(duration_ms, 2),
        )

    def score_file(
        self,
        goal: str,
        goal_tokens: Set[str],
        file_meta: ScannedFileMetadata,
        preferred_types: Optional[Set[str]] = None,
        recency_focus: bool = False,
    ) -> Tuple[float, str]:
        """Compute composite relevance score and explanatory reason for a file."""
        name_lower = file_meta.name.lower()
        path_lower = file_meta.relative_path.lower()
        ext_clean = file_meta.extension.lstrip(".").lower()

        name_tokens = tokenize(file_meta.name)
        path_tokens = tokenize(file_meta.relative_path)
        all_file_tokens = name_tokens | path_tokens

        filename_score = 0.0
        path_score = 0.0
        type_score = 0.0
        recency_score = 0.0
        peek_score = 0.0
        reasons: List[str] = []

        # 1. Filename matching
        stem = Path(file_meta.name).stem.lower()

        # Token normalization & stemming: remove trailing digits and plural 's'
        overlap_direct = [
            t for t in goal_tokens
            if (len(t) >= 3 and t in name_lower)
            or any(t.rstrip("s") in nt or nt.rstrip("0123456789_") in t for nt in name_tokens)
        ]

        is_auth_goal = any(term in goal.lower() for term in AUTH_SYNONYMS)
        is_auth_file = any(term in name_lower or term in path_lower for term in AUTH_SYNONYMS)

        if overlap_direct:
            filename_score = min(0.45, 0.25 + 0.10 * len(overlap_direct))
            reasons.append(f"filename matches task terms ({', '.join(sorted(overlap_direct)[:2])})")
        elif is_auth_goal and is_auth_file:
            filename_score = 0.35
            reasons.append("authentication/login module matches task")
        elif goal_tokens & name_tokens:
            overlap = goal_tokens & name_tokens
            filename_score = min(0.35, 0.15 + 0.10 * len(overlap))
            reasons.append(f"filename contains keywords ({', '.join(sorted(overlap)[:2])})")

        # 2. Path matching
        if any(t in path_lower for t in goal_tokens if len(t) >= 4):
            path_score = 0.15
            reasons.append("path matches task context")

        # 3. File type & domain boost
        is_data_task = any(kw in goal.lower() for kw in DATA_KEYWORDS)
        is_doc_task = any(kw in goal.lower() for kw in DOC_KEYWORDS)
        is_code_task = any(kw in goal.lower() for kw in CODE_KEYWORDS)

        if preferred_types and ext_clean in preferred_types:
            type_score = 0.25
            reasons.append(f"file type ({ext_clean}) matches preferred format")
        elif is_data_task and file_meta.category == FileCategory.STRUCTURED_DATA:
            type_score = 0.25
            reasons.append("structured data format matches data analysis task")
        elif is_doc_task and file_meta.category == FileCategory.DOCUMENT:
            type_score = 0.25
            reasons.append("document format matches research task")
        elif is_code_task and file_meta.category == FileCategory.SOURCE_CODE:
            type_score = 0.25
            reasons.append("source code matches coding task")

        # 4. Recency boost
        now = datetime.now(timezone.utc)
        age_hours = (now - file_meta.modified_at).total_seconds() / 3600.0

        if recency_focus:
            # Task explicitly asked for "yesterday" or "recent"
            if age_hours <= 48:
                recency_score = 0.15
                reasons.append("recently modified matching temporal constraint")
            elif age_hours <= 168:  # 1 week
                recency_score = 0.08
        else:
            # Mild general recency bias
            if age_hours <= 24:
                recency_score = 0.05

        # 5. Content peek for text files (first 5 lines)
        if not file_meta.is_binary and file_meta.size_bytes > 0 and file_meta.size_bytes < 5_000_000:
            peek_matches = self._peek_file_relevance(file_meta.absolute_path, goal_tokens)
            if peek_matches > 0:
                peek_score = min(0.10, 0.05 * peek_matches)
                reasons.append("header/content preview aligns with task")

        # Composite score
        raw_score = filename_score + path_score + type_score + recency_score + peek_score
        final_score = min(1.0, max(0.0, raw_score))

        # Build safe explanation
        reason_str = "; ".join(reasons) if reasons else "general match in authorized workspace"
        full_reason = f"{reason_str} (score: {final_score:.2f})"

        return final_score, full_reason

    def _peek_file_relevance(self, path: Path, goal_tokens: Set[str]) -> int:
        """Safely read header / top lines to check for keyword presence."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                header_lines = [f.readline().lower() for _ in range(5)]
            text = " ".join(header_lines)
            return sum(1 for token in goal_tokens if len(token) >= 3 and token in text)
        except Exception:
            return 0

    def evaluate_ambiguity(
        self,
        candidates: List[CandidateFile],
        goal: str,
    ) -> Tuple[List[CandidateFile], bool, Optional[str]]:
        """Evaluate ranked candidates to determine automatic selection or clarification.

        Returns:
            (selected_candidates, ambiguity_detected, clarification_message)
        """
        # Case 1: No candidates found
        if not candidates:
            msg = (
                f"No relevant files found in authorized workspace for task: '{goal}'. "
                "Please verify that the workspace contains the expected files."
            )
            return [], False, msg

        top = candidates[0]

        # Case 2: Top candidate is below minimum confidence threshold
        if top.score < self.min_score_threshold:
            msg = (
                f"No relevant files found in authorized workspace for: '{goal}'. "
                f"Best candidate was '{top.relative_path}' with low confidence ({top.score:.2f})."
            )
            return [], False, msg

        # Check if the goal indicates multi-file usage (e.g. "Use my research papers and project requirements")
        goal_lower = goal.lower()
        is_multi_file_goal = any(trigger in goal_lower for trigger in MULTI_FILE_TRIGGERS)

        if is_multi_file_goal:
            # Select all high-confidence candidates
            high_conf = [c for c in candidates if c.score >= 0.50]
            if len(high_conf) > 1:
                return high_conf, False, None

        # Case 3: Exactly one candidate or dominant top candidate
        if len(candidates) == 1:
            return [top], False, None

        second = candidates[1]
        score_diff = top.score - second.score

        # Case 4: Ambiguity! Multiple top candidates with very close high scores
        if top.score >= self.auto_select_threshold and score_diff <= self.ambiguity_margin:
            # Equi-relevant candidates
            equal_candidates = [
                c for c in candidates
                if (top.score - c.score) <= self.ambiguity_margin
            ][:3]

            names = "\n".join(f"- {c.relative_path} ({c.reason})" for c in equal_candidates)
            clarification = (
                f"I found multiple likely files matching your request:\n{names}\n\n"
                "Which one would you like me to use?"
            )
            return equal_candidates, True, clarification

        # Case 5: Clear dominant match
        return [top], False, None


__all__ = [
    "RelevanceRanker",
    "DATA_KEYWORDS",
    "DOC_KEYWORDS",
    "CODE_KEYWORDS",
    "RECENCY_KEYWORDS",
]
