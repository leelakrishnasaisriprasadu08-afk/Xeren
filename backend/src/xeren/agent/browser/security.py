"""Security boundaries, filesystem constraints, and secret redaction for browser adapters."""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from xeren.agent.browser.errors import BrowserSecurityError


class BrowserSecurityManager:
    """Enforces safety rules, path restrictions, and credential sanitization."""

    # Sensitive key names to redact
    SENSITIVE_FIELD_NAMES: Set[str] = {
        "password",
        "passwd",
        "secret",
        "token",
        "auth",
        "authorization",
        "bearer",
        "api_key",
        "apikey",
        "access_token",
        "cookie",
        "set-cookie",
        "session",
        "session_id",
        "private_key",
    }

    # Regex patterns for common credentials
    SENSITIVE_PATTERNS: List[re.Pattern] = [
        re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
        re.compile(r"(Basic\s+)[A-Za-z0-9+/=]{10,}", re.IGNORECASE),
        re.compile(r"(sk-[A-Za-z0-9]{20,})", re.IGNORECASE),
        re.compile(r"(ghp_[A-Za-z0-9]{20,})", re.IGNORECASE),
        re.compile(r"(AKIA[0-9A-Z]{16})"),
        re.compile(r"(AIza[0-9A-Za-z-_]{35})"),
        re.compile(r"(password\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE),
    ]

    ALLOWED_SCHEMES: Set[str] = {"http", "https", "file", "about"}

    def __init__(
        self,
        allowed_workspace_dir: Optional[Union[str, Path]] = None,
        allowed_upload_dir: Optional[Union[str, Path]] = None,
        allowed_download_dir: Optional[Union[str, Path]] = None,
        allowed_domains: Optional[List[str]] = None,
    ) -> None:
        self.workspace_dir = Path(allowed_workspace_dir or Path.cwd()).resolve()
        self.upload_dir = Path(allowed_upload_dir or self.workspace_dir).resolve()
        self.download_dir = Path(allowed_download_dir or self.workspace_dir).resolve()
        self.allowed_domains = set(allowed_domains) if allowed_domains else None

        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> str:
        """Validate that a URL uses an approved protocol and doesn't violate safety policies."""
        if not url or not isinstance(url, str):
            raise BrowserSecurityError("URL must be a non-empty string.")

        cleaned_url = url.strip()
        parsed = urlparse(cleaned_url)

        scheme = parsed.scheme.lower()
        if not scheme:
            # Treat bare domains as https
            cleaned_url = f"https://{cleaned_url}"
            parsed = urlparse(cleaned_url)
            scheme = parsed.scheme.lower()

        if scheme not in self.ALLOWED_SCHEMES:
            raise BrowserSecurityError(
                f"URL scheme '{scheme}' is forbidden. Allowed schemes: {self.ALLOWED_SCHEMES}",
                url=cleaned_url,
            )

        # Dangerous pseudo-schemes
        if scheme in {"javascript", "data", "vbscript"}:
            raise BrowserSecurityError(
                f"Execution of '{scheme}:' scripts via browser navigation is prohibited.",
                url=cleaned_url,
            )

        # For file:// URLs, ensure they point strictly inside the allowed workspace
        if scheme == "file":
            # Extract path from file URI
            file_path_str = parsed.path
            # Windows file URI normalization: /C:/path -> C:/path
            if len(file_path_str) > 2 and file_path_str[0] == "/" and file_path_str[2] == ":":
                file_path_str = file_path_str[1:]
            target_path = Path(file_path_str).resolve()
            try:
                target_path.relative_to(self.workspace_dir)
            except ValueError:
                raise BrowserSecurityError(
                    f"Access to file '{target_path}' outside workspace '{self.workspace_dir}' is denied.",
                    url=cleaned_url,
                )

        if self.allowed_domains and parsed.netloc:
            domain = parsed.netloc.split(":")[0].lower()
            if not any(domain == d or domain.endswith(f".{d}") for d in self.allowed_domains):
                raise BrowserSecurityError(
                    f"Navigation to domain '{domain}' is not in allowed domains list.",
                    url=cleaned_url,
                )

        return cleaned_url

    def validate_upload_path(self, file_path: Union[str, Path]) -> Path:
        """Ensure file to upload exists and is strictly within the allowed upload directory."""
        path = Path(file_path).resolve()

        try:
            path.relative_to(self.upload_dir)
        except ValueError:
            raise BrowserSecurityError(
                f"Upload rejected: Path '{path}' is outside approved upload directory '{self.upload_dir}'.",
                details={"target_path": str(path), "upload_dir": str(self.upload_dir)},
            )

        if not path.exists():
            raise BrowserSecurityError(
                f"Upload rejected: File does not exist at '{path}'.",
                details={"target_path": str(path)},
            )

        if not path.is_file():
            raise BrowserSecurityError(
                f"Upload rejected: Target '{path}' is not a regular file.",
                details={"target_path": str(path)},
            )

        return path

    def validate_download_path(self, target_path: Optional[Union[str, Path]] = None, filename: Optional[str] = None) -> Path:
        """Ensure destination path for a download is strictly within the allowed download directory."""
        if target_path:
            dest = Path(target_path).resolve()
        elif filename:
            # Strip any directory components from filename
            safe_name = Path(filename).name
            dest = (self.download_dir / safe_name).resolve()
        else:
            dest = self.download_dir.resolve()

        # If dest is a directory, ensure it is within download_dir
        if dest.is_dir() or (not dest.exists() and not dest.suffix):
            try:
                dest.relative_to(self.download_dir)
            except ValueError:
                raise BrowserSecurityError(
                    f"Download rejected: Directory '{dest}' is outside approved download directory '{self.download_dir}'.",
                    details={"target_path": str(dest), "download_dir": str(self.download_dir)},
                )
            return dest

        # If dest is a file, ensure its parent directory is within download_dir
        try:
            dest.parent.relative_to(self.download_dir)
        except ValueError:
            raise BrowserSecurityError(
                f"Download rejected: Destination '{dest}' is outside approved download directory '{self.download_dir}'.",
                details={"target_path": str(dest), "download_dir": str(self.download_dir)},
            )

        return dest

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Redact sensitive credentials, auth tokens, and passwords from raw strings."""
        if not text:
            return ""

        sanitized = text
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive keys and values from dictionaries."""
        sanitized: Dict[str, Any] = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in cls.SENSITIVE_FIELD_NAMES):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = cls.sanitize_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    cls.sanitize_dict(item) if isinstance(item, dict)
                    else (cls.sanitize_text(item) if isinstance(item, str) else item)
                    for item in v
                ]
            elif isinstance(v, str):
                sanitized[k] = cls.sanitize_text(v)
            else:
                sanitized[k] = v
        return sanitized
