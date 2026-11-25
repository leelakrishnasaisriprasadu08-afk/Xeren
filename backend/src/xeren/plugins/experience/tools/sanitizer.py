"""Best-effort credential and secret sanitization for experience records."""

import re
from typing import Any, Dict, List, Optional, Tuple

SECRET_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # OpenAI and OpenAI-like keys (sk-...)
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,})\b"), "[REDACTED_API_KEY]"),
    # AWS Access Key IDs
    (re.compile(r"\b(?:AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"\b(?:ghp_[A-Za-z0-9]{36})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-\._~\+\/]{20,}\b"), "Bearer [REDACTED_TOKEN]"),
    # Generic key-value credentials (e.g. password="xyz", api_key="xyz")
    (
        re.compile(
            r"""(?i)(password|secret|token|api_key|auth_token|client_secret)\s*[:=]\s*['"][^'"]{6,}['"]"""
        ),
        r"\1='[REDACTED]'",
    ),
    # Private Key blocks
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


class ExperienceSanitizerTool:
    """Sanitizes text, payloads, and experience attributes to prevent accidental secret leakage."""

    def sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """Redact known credentials and API key patterns from text."""
        if not text or not isinstance(text, str):
            return text

        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def sanitize_payload(self, val: Any) -> Any:
        """Recursively scrub strings within dicts, lists, and primitives."""
        if isinstance(val, str):
            return self.sanitize_text(val)
        if isinstance(val, dict):
            return {
                self.sanitize_text(str(k)): self.sanitize_payload(v)
                for k, v in val.items()
            }
        if isinstance(val, list):
            return [self.sanitize_payload(v) for v in val]
        return val


__all__ = ["ExperienceSanitizerTool", "SECRET_PATTERNS"]
