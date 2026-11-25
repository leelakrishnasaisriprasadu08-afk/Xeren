"""
Xeren Sovereign Pattern DB — Signature Normalizer & doc2query Generator
========================================================================
Extracts parameter-stripped structural signatures for instant clustering and deduplication.
Generates 3-5 doc2query questions (embedding what people will ask, not just what was stored).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple

from .models import PatternCorner


class PatternSignatureNormalizer:
    """Normalizes raw pattern data into canonical structural signatures and doc2query questions."""

    @staticmethod
    def extract_signature(corner: PatternCorner, raw_data: Dict[str, Any]) -> str:
        """Strip variable parameters, paths, timestamps, and memory addresses to derive pure structure."""
        if corner == PatternCorner.WORKFLOW:
            steps = raw_data.get("steps", [])
            action_names = []
            for s in steps:
                if isinstance(s, dict):
                    action_names.append(s.get("action", s.get("name", "unknown")))
                else:
                    action_names.append(str(s))
            canonical_str = "->".join(f"step:{a.strip().lower()}" for a in action_names)
            return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]

        elif corner == PatternCorner.FAILURE_FIX:
            err = str(raw_data.get("error", raw_data.get("error_message", "")))
            # Strip hex addresses, numbers, file paths, and timestamps
            clean_err = re.sub(r"0x[0-9a-fA-F]+", "<ADDR>", err)
            clean_err = re.sub(r"(/[a-zA-Z0-9_\-\.]+)+|[a-zA-Z]:\\[a-zA-Z0-9_\-\.\\]+", "<PATH>", clean_err)
            clean_err = re.sub(r"\b\d+\b", "<NUM>", clean_err)
            clean_err = re.sub(r"\s+", " ", clean_err).strip().lower()
            return hashlib.sha256(clean_err.encode("utf-8")).hexdigest()[:16]

        elif corner == PatternCorner.TOOL_SCHEMA:
            name = str(raw_data.get("name", "")).strip().lower()
            params = sorted(list(raw_data.get("parameters", {}).keys()))
            canonical = f"tool:{name}({','.join(params)})"
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

        elif corner == PatternCorner.RULES_PERMISSIONS:
            subject = str(raw_data.get("subject", raw_data.get("role", ""))).strip().lower()
            action = str(raw_data.get("action", "")).strip().lower()
            resource = str(raw_data.get("resource", "")).strip().lower()
            canonical = f"rule:{subject}:{action}:{resource}"
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

        elif corner == PatternCorner.INTENT_SOLUTION:
            intent = str(raw_data.get("intent", raw_data.get("objective", ""))).strip().lower()
            clean_intent = re.sub(r"[^\w\s]", "", intent)
            words = sorted(list(set(clean_intent.split())))
            canonical = "intent:" + "_".join(words[:6])
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

        else:
            # Fallback for execution traces, entity state, web, episodic
            key_items = sorted([f"{k}:{v}" for k, v in raw_data.items() if k not in ("created_at", "timestamp")])
            canonical = "|".join(key_items[:5])
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def generate_doc2query(corner: PatternCorner, raw_data: Dict[str, Any], summary: str) -> List[str]:
        """Generate 3-5 synthetic search questions matching human search intent."""
        questions: List[str] = []

        if corner == PatternCorner.WORKFLOW:
            name = raw_data.get("name", "process")
            goal = raw_data.get("goal", summary)
            questions = [
                f"How do I execute {name}?",
                f"What is the workflow for {goal}?",
                f"Steps required to complete {name}",
                f"DAG pipeline definition for {goal}",
            ]
        elif corner == PatternCorner.FAILURE_FIX:
            err = raw_data.get("error_type", raw_data.get("error", "runtime error"))
            cause = raw_data.get("root_cause", "")
            questions = [
                f"How do I fix {err}?",
                f"Why did my task fail with {err}?",
                f"Resolution steps for {cause}",
                f"Workaround for {err} in execution pipeline",
            ]
        elif corner == PatternCorner.TOOL_SCHEMA:
            name = raw_data.get("name", "tool")
            desc = raw_data.get("description", summary)
            questions = [
                f"Which tool should I use to {desc}?",
                f"Parameters and schema for {name}",
                f"How to call {name} tool?",
            ]
        elif corner == PatternCorner.RULES_PERMISSIONS:
            action = raw_data.get("action", "operation")
            resource = raw_data.get("resource", "file")
            questions = [
                f"Is the agent permitted to {action} on {resource}?",
                f"What are the access rules for {resource}?",
                f"Security policy governing {action}",
            ]
        elif corner == PatternCorner.INTENT_SOLUTION:
            intent = raw_data.get("intent", summary)
            questions = [
                f"How to accomplish: {intent}?",
                f"Best workflow to handle {intent}",
                f"Proven solution for {intent}",
            ]
        else:
            questions = [
                summary,
                f"Information regarding {summary[:40]}",
                f"Status and record for {summary[:40]}",
            ]

        return [q.strip() for q in questions if q.strip()]
