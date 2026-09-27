"""Secret redaction and sensitive information scrubbing tool for Xeren API."""

import re
from typing import Any, Dict, List, Optional, Tuple

# Regex patterns for detecting and scrubbing sensitive credentials and paths
SECRET_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # Xeren API Keys (e.g. xrn_live_..., xrn_test_..., xrn_...)
    (re.compile(r"\b(?:xrn_(?:live|test)_[A-Za-z0-9_]{16,})\b"), "[REDACTED_XEREN_KEY]"),
    (re.compile(r"\b(?:xrn_[A-Za-z0-9_]{20,})\b"), "[REDACTED_XEREN_KEY]"),
    # OpenAI & generic sk- keys
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,})\b"), "[REDACTED_API_KEY]"),
    # AWS Access Key IDs
    (re.compile(r"\b(?:AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Tokens
    (re.compile(r"\b(?:ghp_[A-Za-z0-9]{36})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Bearer authorization tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-\._~\+\/]{20,}\b"), "Bearer [REDACTED_TOKEN]"),
    # Key-value secret assignments (e.g. password="...", api_key="...", client_secret="...")
    (
        re.compile(
            r"""(?i)(password|secret|token|api_key|auth_token|client_secret|access_key)\s*[:=]\s*['"][^'"]{4,}['"]"""
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
    # Internal filesystem absolute paths
    (re.compile(r"[a-zA-Z]:\\(?:Users|Windows|Program Files|AppData)\\[a-zA-Z0-9_\-\\\.]+"), "[REDACTED_PATH]"),
    (re.compile(r"/(?:home|etc|proc|sys|root|var)/[a-zA-Z0-9_\-/\.]+"), "[REDACTED_PATH]"),
]

SENSITIVE_HEADER_KEYS = frozenset([
    "authorization",
    "x-api-key",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-auth-token",
])


class ApiSecretRedactorTool:
    """Sanitizes text, headers, payloads, and error messages to prevent credential leakage."""

    def sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """Redact sensitive patterns and credentials from a text string."""
        if not text or not isinstance(text, str):
            return text

        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def sanitize_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Scrub known authorization and secret header values."""
        if not headers:
            return {}

        clean_headers: Dict[str, str] = {}
        for k, v in headers.items():
            if k.lower() in SENSITIVE_HEADER_KEYS:
                # Mask secret header while preserving prefix if Bearer
                if v.lower().startswith("bearer "):
                    clean_headers[k] = "Bearer [REDACTED]"
                else:
                    clean_headers[k] = "[REDACTED]"
            else:
                clean_headers[k] = self.sanitize_text(str(v)) or ""
        return clean_headers

    def sanitize_payload(self, val: Any) -> Any:
        """Recursively scrub data structures (dicts, lists, and primitives)."""
        if isinstance(val, str):
            return self.sanitize_text(val)
        if isinstance(val, dict):
            clean_dict: Dict[str, Any] = {}
            for k, v in val.items():
                k_str = str(k)
                # If key itself is a sensitive name, mask value immediately
                if k_str.lower() in ("api_key", "password", "token", "client_secret", "secret"):
                    clean_dict[self.sanitize_text(k_str) or k_str] = "[REDACTED]"
                else:
                    clean_dict[self.sanitize_text(k_str) or k_str] = self.sanitize_payload(v)
            return clean_dict
        if isinstance(val, list):
            return [self.sanitize_payload(item) for item in val]
        return val


__all__ = ["ApiSecretRedactorTool", "SECRET_PATTERNS", "SENSITIVE_HEADER_KEYS"]
