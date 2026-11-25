"""
Xeren Sovereign Pattern DB — Pattern Query Router
=================================================
Labels queries before search and routes directly to matching partitions (5% scan vs 100%).
Eliminates cross-partition noise and prevents wrong-corner hallucinations.
Supports 2-3 corner fan-out for ambiguous queries with Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import PatternCorner


class PatternQueryRouter:
    """Pre-search query discriminator routing search intents to specialized corners."""

    ROUTING_RULES: List[Tuple[re.Pattern, List[PatternCorner], float]] = [
        # 1. Error / Failure Diagnosis & Fixing
        (
            re.compile(
                r"\b(error|failed|failure|exception|crash|traceback|fix|errno|syntaxerror|broken|bug|resolution|resolve|timeout|timed out|deadline exceeded)\b",
                re.I,
            ),
            [PatternCorner.FAILURE_FIX, PatternCorner.EXECUTION_TRACE],
            0.95,
        ),
        # 2. Security Rules & Permissions (Preloaded/Zero-vector lookup)
        (
            re.compile(
                r"\b(rule|rules|permission|permissions|allowed|forbidden|sandbox|policy|privilege|access)\b|can\s+.*agent",
                re.I,
            ),
            [PatternCorner.RULES_PERMISSIONS],
            0.98,
        ),
        # 3. Intent -> Solution Cases & Actionable Goals
        (
            re.compile(
                r"\b(how to|backup|report|generate|automate|automated|sync|dispatch|onboard a user|send weekly)\b",
                re.I,
            ),
            [PatternCorner.INTENT_SOLUTION, PatternCorner.WORKFLOW],
            0.94,
        ),
        # 4. Workflow Definitions & Multi-step Pipelines
        (
            re.compile(
                r"\b(workflow|dag|pipeline|step-by-step|steps to|how to onboard|process for|procedure)\b",
                re.I,
            ),
            [PatternCorner.WORKFLOW, PatternCorner.INTENT_SOLUTION],
            0.92,
        ),
        # 4. Tool & API Specifications
        (
            re.compile(r"\b(tool|function|api|parameter|arguments|schema|signature|endpoint|method|call)\b", re.I),
            [PatternCorner.TOOL_SCHEMA],
            0.90,
        ),
        # 5. Entity & Resource State (Relational/KV exact lookup)
        (
            re.compile(r"\b(status of|state of|current user|resource state|file status|table schema)\b", re.I),
            [PatternCorner.ENTITY_STATE],
            0.88,
        ),
        # 6. Volatile / Web Knowledge (TTL-checked)
        (
            re.compile(r"\b(latest|current|live|price|fresh|today|news|release notes|changelog)\b", re.I),
            [PatternCorner.VOLATILE_WEB, PatternCorner.INTENT_SOLUTION],
            0.85,
        ),
        # 7. Episodic / Agent History
        (
            re.compile(r"\b(last time|previous run|earlier|what did you do|history|yesterday|past task)\b", re.I),
            [PatternCorner.EPISODIC_MEMORY],
            0.90,
        ),
    ]

    @classmethod
    def route(cls, query: str) -> List[Tuple[PatternCorner, float]]:
        """
        Classifies user query and returns ranked target corners with confidence weights.
        Defaults to [INTENT_SOLUTION, WORKFLOW] if no specific pattern triggers match.
        """
        clean_q = query.strip()
        matched_corners: Dict[PatternCorner, float] = {}

        for pattern, corners, confidence in cls.ROUTING_RULES:
            if pattern.search(clean_q):
                for c in corners:
                    matched_corners[c] = max(matched_corners.get(c, 0.0), confidence)

        if not matched_corners:
            # Default fallback for general intent queries
            matched_corners[PatternCorner.INTENT_SOLUTION] = 0.70
            matched_corners[PatternCorner.WORKFLOW] = 0.50

        # Return sorted by confidence descending
        return sorted(matched_corners.items(), key=lambda x: x[1], reverse=True)
