"""
Xeren ExperienceStore Causal Engine — Causal Distiller
=====================================================
Transforms raw execution traces (Action, Result, Error) into structured causal lessons:
- If Success: extracts the invariant operational success strategy.
- If Failure/Retry: diagnoses the deterministic root cause and formulates a preventative new strategy.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from .models import CausalTuple, ReviewStatus

logger = logging.getLogger("xeren.core.experience.distiller")


class CausalDistiller:
    """Distills causal lessons from execution outcomes using pattern diagnostics and heuristics."""

    FAILURE_PATTERNS = [
        (
            re.compile(r"(permission denied|access denied|forbidden|eacces|unauthorized)", re.I),
            "INSUFFICIENT_PERMISSIONS",
            "Target path or resource requires elevated privileges or is outside the permitted sandbox.",
            "Verify path boundaries against workspace root and request user step-up authentication if required.",
        ),
        (
            re.compile(r"(no such file|file not found|notfounderror|enoent|does not exist)", re.I),
            "RESOURCE_NOT_FOUND",
            "Referenced file, directory, or database table does not exist at the specified path.",
            "Verify path existence, check for typos, and ensure parent directories exist before accessing.",
        ),
        (
            re.compile(r"(timeout|timed out|timeouterror|deadline exceeded)", re.I),
            "EXECUTION_TIMEOUT",
            "Operation exceeded allotted latency deadline or async event loop blocked.",
            "Partition workload into smaller chunks, apply exponential backoff, or execute via background task.",
        ),
        (
            re.compile(r"(syntaxerror|invalid syntax|unexpected token|indentationerror)", re.I),
            "SYNTAX_PARSE_ERROR",
            "Synthesized code failed native AST parsing due to unbalanced brackets, keywords, or invalid syntax.",
            "Pass code through ast.parse before submission and correct line-level syntax issues.",
        ),
        (
            re.compile(r"(connection refused|econnrefused|connecterror|network is unreachable)", re.I),
            "CONNECTION_FAILURE",
            "Remote endpoint, database socket, or external daemon is unreachable or down.",
            "Verify local socket/service availability, implement retry with jitter, or failover to local fallback.",
        ),
        (
            re.compile(r"(rate limit|quota exceeded|429|too many requests)", re.I),
            "RATE_LIMIT_EXCEEDED",
            "API rate limit or governor quota was exceeded during burst traffic.",
            "Route through CAG semantic cache or buffer requests via AdaptiveUsageGovernor token bucket.",
        ),
        (
            re.compile(r"(keyerror|missing key|indexerror|out of range)", re.I),
            "DATA_STRUCTURE_LOOKUP_ERROR",
            "Attempted to access non-existent key or index without boundary validation.",
            "Use dict.get(key, default) or validate collection bounds prior to indexing.",
        ),
    ]

    def distill(
        self,
        task_id: str,
        objective: str,
        action: str,
        result: str,
        success: bool,
        error: Optional[str] = None,
        verification_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CausalTuple:
        """Distill an execution trace into a CausalTuple with root cause and strategy."""
        meta = metadata or {}
        combined_text = f"{result} {error or ''}".strip()

        if success:
            root_cause = "Operational parameters, arguments, and environment constraints were satisfied."
            new_strategy = f"Employ '{action}' with verified argument contracts when pursuing '{objective}'."
            status = ReviewStatus.APPROVED if verification_score >= 0.8 else ReviewStatus.UNREVIEWED
        else:
            diagnosed_cause = None
            suggested_strategy = None

            for pattern, category, cause_desc, strategy_desc in self.FAILURE_PATTERNS:
                if pattern.search(combined_text):
                    diagnosed_cause = f"[{category}] {cause_desc}"
                    suggested_strategy = strategy_desc
                    break

            if not diagnosed_cause:
                diagnosed_cause = f"[UNCLASSIFIED_FAILURE] {error or result[:200]}"
                suggested_strategy = "Inspect stack trace, validate pre-conditions, and retry with isolated arguments."

            root_cause = diagnosed_cause
            new_strategy = suggested_strategy
            status = ReviewStatus.UNREVIEWED

        causal_tuple = CausalTuple(
            task_id=task_id,
            objective=objective,
            action=action,
            result=result,
            success=success,
            root_cause=root_cause,
            new_strategy=new_strategy,
            verification_score=verification_score,
            status=status,
            metadata=meta,
        )

        logger.debug(
            "[Distiller] Distilled causal tuple for task '%s' (success=%s, fingerprint=%s)",
            task_id,
            success,
            causal_tuple.fingerprint[:8],
        )
        return causal_tuple
