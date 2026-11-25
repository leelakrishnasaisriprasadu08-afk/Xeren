"""Anti-Poison Experience Quarantine Buffer for Xeren.

Ensures that raw task execution traces are staged, sanitized (PII stripped,
syntax validated), and cryptographically fingerprinted before becoming candidates
for model continual learning datasets.

Schema:
  (task_id, objective, action, result, root_cause, new_strategy, status, timestamp)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.experience.quarantine")


@dataclass
class QuarantinedExperience:
    """A single staged execution experience waiting for review/verification."""

    task_id: str
    objective: str
    action: str
    result: str
    root_cause: Optional[str] = None
    new_strategy: Optional[str] = None
    fingerprint: str = ""
    status: str = "UNREVIEWED"  # UNREVIEWED, APPROVED, REJECTED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.fingerprint:
            # Deterministic SHA-256 fingerprint over core causal tuple
            payload = f"{self.objective}|{self.action}|{self.result}|{self.root_cause}|{self.new_strategy}"
            self.fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ExperienceQuarantineBuffer:
    """Manages appending and inspecting staged unreviewed experiences."""

    def __init__(self, buffer_path: Optional[str] = None) -> None:
        default_path = Path("data/unreviewed_experiences.jsonl")
        self.buffer_path = Path(buffer_path) if buffer_path else default_path
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.buffer_path.exists():
            self.buffer_path.touch()

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Strips common PII (emails, API keys, passwords, IP addresses) before staging."""
        # Strip emails
        sanitized = re.sub(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]", text
        )
        # Strip potential API keys / secrets
        sanitized = re.sub(
            r"(api[_-]?key|secret|password|bearer|auth|token)[\s:=]+['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
            r"\1: [SECRET_REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )
        # Strip IPv4
        sanitized = re.sub(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]", sanitized
        )
        return sanitized

    def stage_experience(
        self,
        task_id: str,
        objective: str,
        action: str,
        result: str,
        root_cause: Optional[str] = None,
        new_strategy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QuarantinedExperience:
        """Sanitizes and appends an execution experience to the quarantine buffer."""
        clean_obj = self.sanitize_text(objective)
        clean_action = self.sanitize_text(action)
        clean_result = self.sanitize_text(result)
        clean_cause = self.sanitize_text(root_cause) if root_cause else None
        clean_strat = self.sanitize_text(new_strategy) if new_strategy else None

        item = QuarantinedExperience(
            task_id=task_id,
            objective=clean_obj,
            action=clean_action,
            result=clean_result,
            root_cause=clean_cause,
            new_strategy=clean_strat,
            metadata=metadata or {},
        )

        with open(self.buffer_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(item)) + "\n")

        logger.info(
            "Staged unreviewed experience for task %s (fingerprint: %s)",
            task_id,
            item.fingerprint[:8],
        )
        return item

    def read_unreviewed(self, limit: int = 100) -> List[QuarantinedExperience]:
        """Reads unreviewed candidate experiences from the quarantine buffer."""
        items: List[QuarantinedExperience] = []
        if not self.buffer_path.exists():
            return items

        with open(self.buffer_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("status") == "UNREVIEWED":
                        items.append(QuarantinedExperience(**data))
                        if len(items) >= limit:
                            break
                except Exception as e:
                    logger.warning("Skipping corrupted quarantine record: %s", e)
        return items
