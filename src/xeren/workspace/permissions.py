"""Security boundary and authorization manager for Xeren Workspace Intelligence.

Enforces:
1. Strict boundary containment within explicitly authorized WorkspaceRoot locations.
2. Prevention of path traversal (../), absolute-path escape, and symlink escapes.
3. Windows reserved device name protection.
4. Protection of sensitive files, secrets, system files, and arbitrary executables.
5. Enforcement of READ_ONLY (default) vs READ_WRITE permission modes.
6. Structured audit logging of all security checks and access decisions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from xeren.workspace.schemas import PermissionMode, WorkspaceRoot

logger = logging.getLogger("xeren.workspace.permissions")

# Windows reserved device names (cannot be accessed or created as files)
WINDOWS_RESERVED_NAMES = frozenset([
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
])

# Dangerous executable extensions blocked from arbitrary execution
DANGEROUS_EXECUTABLE_EXTS = frozenset([
    ".exe", ".bat", ".cmd", ".com", ".msi", ".dll", ".sys", ".drv",
    ".vbs", ".vbe", ".wsf", ".wsh", ".scr", ".pif", ".cpl",
])

# Sensitive filenames or patterns that must never be exposed or loaded
SENSITIVE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^id_rsa.*$", re.IGNORECASE),
    re.compile(r"^id_ed25519.*$", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r"^credentials(\.json|\.yaml|\.ini)?$", re.IGNORECASE),
    re.compile(r"^shadow$", re.IGNORECASE),
    re.compile(r"^passwd$", re.IGNORECASE),
]

# Noise / system directories restricted from scanning and access
RESTRICTED_DIRECTORIES = frozenset([
    ".git", ".svn", ".hg", "__pycache__", ".venv", "venv", "node_modules",
    ".idea", ".vscode", ".pytest_cache", ".tox",
])


class WorkspaceSecurityError(Exception):
    """Base exception for workspace security violations."""
    pass


class PathTraversalError(WorkspaceSecurityError):
    """Raised when an operation attempts to escape an authorized root."""
    pass


class UnauthorizedRootError(WorkspaceSecurityError):
    """Raised when an operation targets an unauthorized or disabled workspace root."""
    pass


class WorkspacePermissionError(WorkspaceSecurityError):
    """Raised when an operation exceeds granted permission levels (e.g. write on READ_ONLY root)."""
    pass


class SecurityViolationError(WorkspaceSecurityError):
    """Raised when accessing sensitive credentials, system files, or prohibited executables."""
    pass


class WorkspacePermissionManager:
    """Core authority governing workspace access boundaries and permission enforcement."""

    def __init__(
        self,
        roots: Optional[Sequence[Union[WorkspaceRoot, Path, str]]] = None,
        default_mode: PermissionMode = PermissionMode.READ_ONLY,
        allow_symlinks_within_root: bool = True,
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10 MB
    ) -> None:
        self.roots: Dict[str, WorkspaceRoot] = {}
        self.default_mode = default_mode
        self.allow_symlinks_within_root = allow_symlinks_within_root
        self.max_file_size_bytes = max_file_size_bytes
        self.audit_log: List[Dict[str, Any]] = []

        if roots:
            for r in roots:
                if isinstance(r, WorkspaceRoot):
                    self.add_root(r)
                else:
                    self.authorize_root(r, permission_mode=default_mode)

    def add_root(self, root: WorkspaceRoot) -> None:
        """Register an explicitly authorized WorkspaceRoot."""
        canonical_path = root.path.resolve()
        validated_root = WorkspaceRoot(
            root_id=root.root_id,
            path=canonical_path,
            permission_mode=root.permission_mode,
            enabled=root.enabled,
            allowed_operations=list(root.allowed_operations),
        )
        self.roots[root.root_id] = validated_root
        logger.info(
            "Authorized workspace root registered: id='%s', path='%s', mode='%s'",
            validated_root.root_id,
            validated_root.path,
            validated_root.permission_mode.value,
        )

    def authorize_root(
        self,
        path: Union[str, Path],
        root_id: Optional[str] = None,
        permission_mode: Optional[PermissionMode] = None,
        allowed_operations: Optional[List[str]] = None,
    ) -> WorkspaceRoot:
        """Helper to authorize a directory path as a workspace root."""
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Cannot authorize non-existent path: {path}")
        if not p.is_dir():
            raise NotADirectoryError(f"Workspace root must be a directory: {path}")

        rid = root_id or p.name or "root"
        mode = permission_mode or self.default_mode
        ops = allowed_operations or (
            ["read", "scan", "search", "write", "delete"]
            if mode == PermissionMode.READ_WRITE
            else ["read", "scan", "search"]
        )

        root = WorkspaceRoot(
            root_id=rid,
            path=p,
            permission_mode=mode,
            enabled=True,
            allowed_operations=ops,
        )
        self.add_root(root)
        return root

    def remove_root(self, root_id: str) -> Optional[WorkspaceRoot]:
        """Remove a root from authorization."""
        removed = self.roots.pop(root_id, None)
        if removed:
            logger.info("Deauthorized workspace root: id='%s'", root_id)
        return removed

    def get_root(self, root_id: str) -> WorkspaceRoot:
        """Retrieve an authorized root by ID."""
        if root_id not in self.roots:
            raise UnauthorizedRootError(f"No authorized workspace root with ID '{root_id}'")
        return self.roots[root_id]

    def list_roots(self, active_only: bool = True) -> List[WorkspaceRoot]:
        """List all authorized workspace roots."""
        if active_only:
            return [r for r in self.roots.values() if r.enabled]
        return list(self.roots.values())

    def validate_path(
        self,
        raw_path: Union[str, Path],
        root_id: Optional[str] = None,
        operation: str = "read",
        must_exist: bool = False,
    ) -> Tuple[Path, WorkspaceRoot]:
        """Validate that raw_path resides strictly within an authorized root.

        Returns (canonical_path, matching_root).
        Raises appropriate WorkspaceSecurityError if policy is violated.
        """
        if not raw_path:
            raise PathTraversalError("Path cannot be empty or None")

        path_str = str(raw_path)
        if "\0" in path_str:
            self._log_violation("null_byte", raw_path, operation)
            raise SecurityViolationError("Null bytes in file paths are strictly prohibited")

        # Determine target roots
        candidate_roots: List[WorkspaceRoot] = []
        if root_id:
            if root_id not in self.roots:
                raise UnauthorizedRootError(f"Target workspace root '{root_id}' is not authorized")
            if not self.roots[root_id].enabled:
                raise UnauthorizedRootError(f"Target workspace root '{root_id}' is disabled")
            candidate_roots = [self.roots[root_id]]
        else:
            candidate_roots = [r for r in self.roots.values() if r.enabled]

        if not candidate_roots:
            raise UnauthorizedRootError("No active authorized workspace roots available")

        # Parse path
        p = Path(path_str)

        # Check Windows reserved device names
        for part in p.parts:
            stem = Path(part).stem.upper()
            if stem in WINDOWS_RESERVED_NAMES:
                self._log_violation("windows_reserved_name", raw_path, operation)
                raise SecurityViolationError(f"Use of reserved device name '{stem}' is strictly prohibited")

        # Resolve candidate against candidate roots
        resolved_path: Optional[Path] = None
        matched_root: Optional[WorkspaceRoot] = None

        for root in candidate_roots:
            if not root.enabled:
                continue

            if p.is_absolute():
                candidate = p.resolve()
            else:
                candidate = (root.path / p).resolve()

            # Boundary containment check
            try:
                candidate.relative_to(root.path)
                resolved_path = candidate
                matched_root = root
                break
            except ValueError:
                continue

        if not resolved_path or not matched_root:
            self._log_violation("path_traversal", raw_path, operation)
            raise PathTraversalError(
                f"Access denied: path '{raw_path}' resolves outside authorized workspace boundaries"
            )

        # Enforce Symlink safety
        if resolved_path.is_symlink() or (resolved_path.exists() and os.path.islink(resolved_path)):
            try:
                real_target = resolved_path.resolve(strict=True)
                try:
                    real_target.relative_to(matched_root.path)
                except ValueError:
                    self._log_violation("symlink_escape", raw_path, operation)
                    raise PathTraversalError(
                        f"Symlink target '{real_target}' escapes authorized workspace root '{matched_root.path}'"
                    )
            except (OSError, RuntimeError) as err:
                if must_exist:
                    raise FileNotFoundError(f"File not found: {raw_path}") from err

        # Verify existence if required
        if must_exist and not resolved_path.exists():
            raise FileNotFoundError(f"File or directory does not exist: {raw_path}")

        # Enforce permission mode for modifying operations
        if operation in ("write", "delete", "create", "modify"):
            if matched_root.permission_mode != PermissionMode.READ_WRITE:
                self._log_violation("permission_denied_read_only", raw_path, operation)
                raise WorkspacePermissionError(
                    f"Write operation '{operation}' denied: workspace root '{matched_root.root_id}' is READ_ONLY"
                )
            if operation not in matched_root.allowed_operations:
                self._log_violation("operation_not_allowed", raw_path, operation)
                raise WorkspacePermissionError(
                    f"Operation '{operation}' not permitted on root '{matched_root.root_id}'"
                )

        # Enforce sensitive file restrictions
        self.check_sensitive_access(resolved_path, operation)

        # Record audit success
        self._log_success(resolved_path, matched_root, operation)
        return resolved_path, matched_root

    def check_sensitive_access(self, target_path: Path, operation: str) -> None:
        """Check for and block access to credentials, private keys, or restricted directories."""
        name = target_path.name

        # Check sensitive filename patterns
        for pat in SENSITIVE_PATTERNS:
            if pat.match(name):
                self._log_violation("sensitive_file_blocked", str(target_path), operation)
                raise SecurityViolationError(f"Access to sensitive file '{name}' is restricted by security policy")

        # Check restricted directory ancestry
        for parent in target_path.parents:
            if parent.name in RESTRICTED_DIRECTORIES:
                # Disallow direct sensitive files inside noise dirs
                if name.startswith(".env") or name.endswith(".key"):
                    self._log_violation("restricted_dir_sensitive_blocked", str(target_path), operation)
                    raise SecurityViolationError(f"Access to sensitive file in '{parent.name}' is restricted")

        # Check dangerous executable access
        if target_path.suffix.lower() in DANGEROUS_EXECUTABLE_EXTS and operation in ("execute", "run"):
            self._log_violation("executable_blocked", str(target_path), operation)
            raise SecurityViolationError(f"Execution of binary '{name}' is prohibited")

    def is_safe_for_scanning(self, path: Path, root: WorkspaceRoot) -> bool:
        """Check whether a path should be included during lightweight metadata scanning."""
        try:
            rel = path.resolve().relative_to(root.path)
        except ValueError:
            return False

        # Exclude restricted directories
        for part in rel.parts:
            if part in RESTRICTED_DIRECTORIES:
                return False
            # Filter hidden files unless needed
            if part.startswith(".") and not part == ".":
                return False

        # Filter sensitive files
        for pat in SENSITIVE_PATTERNS:
            if pat.match(path.name):
                return False

        return True

    def get_relative_path(self, target_path: Path, root: Optional[WorkspaceRoot] = None) -> str:
        """Convert a path into a safe, normalized relative path with forward slashes."""
        resolved = target_path.resolve()
        if root:
            try:
                return resolved.relative_to(root.path).as_posix()
            except ValueError:
                pass

        for r in self.roots.values():
            try:
                return resolved.relative_to(r.path).as_posix()
            except ValueError:
                continue

        return resolved.name

    def _log_violation(self, violation_type: str, path: Union[str, Path], operation: str) -> None:
        record = {
            "status": "VIOLATION",
            "type": violation_type,
            "path": str(path),
            "operation": operation,
        }
        self.audit_log.append(record)
        logger.warning("Workspace security violation [%s]: operation='%s' on path='%s'", violation_type, operation, path)

    def _log_success(self, path: Path, root: WorkspaceRoot, operation: str) -> None:
        record = {
            "status": "ALLOWED",
            "root_id": root.root_id,
            "path": str(path),
            "operation": operation,
        }
        self.audit_log.append(record)


__all__ = [
    "WorkspacePermissionManager",
    "WorkspaceSecurityError",
    "PathTraversalError",
    "UnauthorizedRootError",
    "WorkspacePermissionError",
    "SecurityViolationError",
    "WINDOWS_RESERVED_NAMES",
    "DANGEROUS_EXECUTABLE_EXTS",
    "RESTRICTED_DIRECTORIES",
]
