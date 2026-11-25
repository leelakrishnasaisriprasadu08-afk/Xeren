"""
Xeren ExperienceStore Causal Engine — Anti-Poison Quarantine Gate
================================================================
Stages unreviewed causal experiences, enforces deep PII and secret sanitization,
and acts as the defensive quarantine barrier before experiences can enter authoritative memory
or continual learning training datasets.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .models import CausalTuple, ReviewStatus

logger = logging.getLogger("xeren.core.experience.quarantine_gate")


class AntiPoisonQuarantineGate:
    """Manages staging, sanitization, and verification review of candidate causal tuples."""

    def __init__(self, staging_path: Optional[Path] = None) -> None:
        self.staging_path = staging_path or Path("data/causal_quarantine.jsonl")
        self.staging_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.staging_path.exists():
            self.staging_path.touch()

    @staticmethod
    def sanitize(text: Optional[str]) -> Optional[str]:
        """Strip sensitive credentials, API keys, tokens, emails, and IPs from text."""
        if not text:
            return text

        # 1. Emails
        sanitized = re.sub(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "[EMAIL_REDACTED]",
            text,
        )

        # 2. Bearer / JWT / API keys
        sanitized = re.sub(
            r"(api[_-]?key|secret|password|bearer|auth|token|jwt)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?",
            r"\1: [SECRET_REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )

        # 3. Private keys
        sanitized = re.sub(
            r"-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----[\s\S]*?-----END \1 PRIVATE KEY-----",
            "[PRIVATE_KEY_REDACTED]",
            sanitized,
        )

        # 4. IPv4 addresses
        sanitized = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]", sanitized)

        return sanitized

    def stage(self, causal_tuple: CausalTuple) -> CausalTuple:
        """Sanitizes text fields, verifies fingerprint, and appends to the staging quarantine log."""
        sanitized_obj = self.sanitize(causal_tuple.objective) or ""
        sanitized_act = self.sanitize(causal_tuple.action) or ""
        sanitized_res = self.sanitize(causal_tuple.result) or ""
        sanitized_cause = self.sanitize(causal_tuple.root_cause)
        sanitized_strat = self.sanitize(causal_tuple.new_strategy)

        clean_tuple = CausalTuple(
            task_id=causal_tuple.task_id,
            objective=sanitized_obj,
            action=sanitized_act,
            result=sanitized_res,
            success=causal_tuple.success,
            root_cause=sanitized_cause,
            new_strategy=sanitized_strat,
            verification_score=causal_tuple.verification_score,
            status=causal_tuple.status,
            metadata=causal_tuple.metadata,
        )

        with open(self.staging_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(clean_tuple.to_dict()) + "\n")

        logger.info(
            "[QuarantineGate] Staged experience for task '%s' (status=%s, fingerprint=%s)",
            clean_tuple.task_id,
            clean_tuple.status.value,
            clean_tuple.fingerprint[:8],
        )
        return clean_tuple

    def list_staged(self, status: Optional[ReviewStatus] = None, limit: int = 100) -> List[CausalTuple]:
        """Read staged tuples from the quarantine log."""
        items: List[CausalTuple] = []
        if not self.staging_path.exists():
            return items

        with open(self.staging_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    t = CausalTuple.from_dict(data)
                    if status is None or t.status == status:
                        items.append(t)
                        if len(items) >= limit:
                            break
                except Exception as e:
                    logger.warning("[QuarantineGate] Skipping corrupt quarantine line: %s", e)
        return items

    def update_status(self, fingerprint: str, new_status: ReviewStatus) -> Optional[CausalTuple]:
        """Update review status of a staged tuple by fingerprint."""
        if not self.staging_path.exists():
            return None

        updated_tuple: Optional[CausalTuple] = None
        all_lines: List[Dict[str, Any]] = []

        with open(self.staging_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("fingerprint") == fingerprint:
                        data["status"] = new_status.value
                        updated_tuple = CausalTuple.from_dict(data)
                    all_lines.append(data)
                except Exception:
                    continue

        if updated_tuple:
            with open(self.staging_path, "w", encoding="utf-8") as f:
                for record in all_lines:
                    f.write(json.dumps(record) + "\n")
            logger.info("[QuarantineGate] Updated fingerprint %s -> %s", fingerprint[:8], new_status.value)

        return updated_tuple
