"""Security boundary and validation engine for the Xeren File Plugin.

Enforces workspace-root authorization, path canonicalization, symlink escape checks,
file size ceilings, and best-effort secret redaction.

Notice: Secret detection and redaction is BEST-EFFORT. It is NOT a guarantee that every
possible secret or token will be detected or removed.
"""

import logging
import os
from pathlib import Path
import re
from typing import List, Optional, Sequence, Tuple, Union

logger = logging.getLogger("xeren.plugins.file.tools.security")

# Windows reserved device names (cannot be used as filenames)
WINDOWS_RESERVED_NAMES = frozenset([
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
])

# Defense-in-depth absolute system prefixes (blocked if outside workspace)
SYSTEM_ROOT_PREFIXES = (
    "/etc", "/proc", "/sys", "/dev", "/var", "/boot", "/root",
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
)

# Best-effort credential and API key regex patterns
SECRET_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # OpenAI and OpenAI-like keys
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,})\b"), "[REDACTED_API_KEY]"),
    # AWS Access Key IDs
    (re.compile(r"\b(?:AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"\b(?:ghp_[A-Za-z0-9]{36})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-\._~\+\/]{20,}\b"), "Bearer [REDACTED_TOKEN]"),
    # Generic key-value credentials (e.g. password="xyz", api_key="xyz")
    (
        re.compile(r"""(?i)(password|secret|token|api_key|auth_token|client_secret)\s*[:=]\s*['"][^'"]{6,}['"]"""),
        r"\1='[REDACTED]'",
    ),
    # Private Key blocks
    (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


class FileSecurityError(Exception):
    """Base exception raised when a filesystem operation violates security policies."""
    pass


class PathTraversalError(FileSecurityError):
    """Raised when an operation attempts to access paths outside the approved workspace boundary."""
    pass


class FileSizeLimitError(FileSecurityError):
    """Raised when an operation exceeds configured file size ceilings."""
    pass


class FileSecurityTool:
    """Core security authority for all Xeren file operations.

    Primary authorization is strictly anchored to the configured workspace root.
    """

    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(
        self,
        workspace_dir: Optional[Union[str, Path]] = None,
        allowed_roots: Optional[Sequence[Union[str, Path]]] = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
        redaction_enabled: bool = True,
    ) -> None:
        self.workspace_dir = Path(workspace_dir).resolve() if workspace_dir else Path.cwd().resolve()
        self.allowed_roots = (
            [Path(r).resolve() for r in allowed_roots]
            if allowed_roots
            else [self.workspace_dir]
        )
        self.max_file_size_bytes = max_file_size_bytes
        self.redaction_enabled = redaction_enabled

    def set_workspace_dir(self, workspace_dir: Union[str, Path]) -> None:
        """Update the active primary workspace directory."""
        self.workspace_dir = Path(workspace_dir).resolve()
        if self.workspace_dir not in self.allowed_roots:
            self.allowed_roots.append(self.workspace_dir)

    def resolve_and_validate_path(
        self,
        raw_path: Union[str, Path],
        must_exist: bool = False,
        check_parent_if_new: bool = True,
    ) -> Path:
        """Canonicalize and validate a path against the primary workspace boundary.

        Enforces:
        1. Non-empty path without null bytes.
        2. Reserved Windows device name protection.
        3. Canonical path resolution within approved workspace root.
        4. Symlink escape detection.
        """
        if not raw_path:
            raise PathTraversalError("Path cannot be empty or None")

        path_str = str(raw_path)
        if "\0" in path_str:
            raise FileSecurityError("Null bytes in file paths are strictly prohibited")

        # Convert to Path object
        p = Path(path_str)

        # Check Windows reserved device names in parts
        for part in p.parts:
            stem = Path(part).stem.upper()
            if stem in WINDOWS_RESERVED_NAMES:
                raise FileSecurityError(f"Use of reserved system device name '{stem}' is prohibited")

        # Normalize relative to workspace directory if relative
        if not p.is_absolute():
            candidate = (self.workspace_dir / p).resolve()
        else:
            candidate = p.resolve()

        # Primary authorization check: must reside inside an approved root
        is_authorized = False
        for approved_root in self.allowed_roots:
            try:
                candidate.relative_to(approved_root)
                is_authorized = True
                break
            except ValueError:
                continue

        if not is_authorized:
            logger.warning("Path traversal blocked: '%s' is outside approved roots", raw_path)
            raise PathTraversalError(
                f"Access denied: path '{raw_path}' resolves outside the approved workspace root '{self.workspace_dir}'"
            )

        # Symlink escape verification (for existing files or symlink targets)
        if candidate.is_symlink() or candidate.exists():
            try:
                real_target = candidate.resolve(strict=True)
                target_authorized = any(
                    self._is_subpath_of(real_target, root) for root in self.allowed_roots
                )
                if not target_authorized:
                    raise PathTraversalError(
                        f"Symlink target '{real_target}' escapes the approved workspace boundary"
                    )
            except (OSError, RuntimeError) as err:
                if must_exist:
                    raise FileNotFoundError(f"File not found: {raw_path}") from err

        if must_exist and not candidate.exists():
            raise FileNotFoundError(f"File or directory does not exist: {raw_path}")

        # If creating new file, verify parent directory resolves within approved roots
        if check_parent_if_new and not candidate.exists():
            parent = candidate.parent
            parent_authorized = any(
                self._is_subpath_of(parent, root) for root in self.allowed_roots
            )
            if not parent_authorized:
                raise PathTraversalError(
                    f"Parent directory of '{raw_path}' escapes the approved workspace boundary"
                )

        return candidate

    @staticmethod
    def _is_subpath_of(child: Path, parent: Path) -> bool:
        """Check if child is located inside parent directory."""
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def validate_size(self, size_bytes: int, limit_override: Optional[int] = None) -> None:
        """Enforce file size limits for read and write operations."""
        limit = limit_override or self.max_file_size_bytes
        if size_bytes > limit:
            raise FileSizeLimitError(
                f"File size ({size_bytes} bytes) exceeds the allowed limit of {limit} bytes"
            )

    def validate_not_workspace_root(self, path: Path, operation_name: str = "delete") -> None:
        """Prevent destructive actions (such as deletion) from targeting the workspace root."""
        resolved = path.resolve()
        for root in self.allowed_roots:
            if resolved == root:
                raise FileSecurityError(
                    f"Cannot perform destructive operation '{operation_name}' on the approved workspace root directory: '{root}'"
                )

    def get_relative_path(self, target_path: Path) -> str:
        """Compute relative path string formatted with forward slashes for cross-platform consistency."""
        for root in self.allowed_roots:
            try:
                rel = target_path.resolve().relative_to(root)
                return rel.as_posix()
            except ValueError:
                continue
        return target_path.as_posix()

    def redact_secrets_if_enabled(
        self, text: Optional[str], enabled: Optional[bool] = None
    ) -> Tuple[Optional[str], bool]:
        """Apply best-effort secret and credential masking to text content.

        Returns:
            Tuple of (sanitized_text, was_redacted).
        """
        if text is None:
            return None, False

        should_redact = self.redaction_enabled if enabled is None else enabled
        if not should_redact or not text:
            return text, False

        sanitized = text
        redaction_occurred = False

        for pattern, replacement in SECRET_PATTERNS:
            new_text, count = pattern.subn(replacement, sanitized)
            if count > 0:
                sanitized = new_text
                redaction_occurred = True

        return sanitized, redaction_occurred


__all__ = [
    "FileSecurityTool",
    "FileSecurityError",
    "PathTraversalError",
    "FileSizeLimitError",
]
