"""Tests for WorkspacePermissionManager: authorization boundaries, path traversal, symlink escapes, and permission modes."""

import os
from pathlib import Path
import pytest

from xeren.workspace.permissions import (
    PathTraversalError,
    SecurityViolationError,
    UnauthorizedRootError,
    WorkspacePermissionError,
    WorkspacePermissionManager,
)
from xeren.workspace.schemas import PermissionMode, WorkspaceRoot


def test_authorized_root_boundary_resolution(tmp_path: Path):
    """Verify legitimate files inside an authorized root resolve cleanly."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path, root_id="test_root")

    sub_dir = tmp_path / "data" / "sub"
    sub_dir.mkdir(parents=True)
    target = sub_dir / "sales.csv"
    target.write_text("date,amount\n2025-01-01,100\n", encoding="utf-8")

    # Relative resolution
    resolved, matched_root = manager.validate_path("data/sub/sales.csv", must_exist=True)
    assert resolved == target.resolve()
    assert matched_root.root_id == "test_root"

    # Absolute resolution
    resolved_abs, _ = manager.validate_path(str(target), must_exist=True)
    assert resolved_abs == target.resolve()


def test_path_traversal_attempts_blocked(tmp_path: Path):
    """Verify traversal outside authorized roots raises PathTraversalError."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path, root_id="sandbox")

    # Directory traversal
    with pytest.raises(PathTraversalError):
        manager.validate_path("../../secret.txt")

    with pytest.raises(PathTraversalError):
        manager.validate_path("..\\..\\secret.txt")

    # Outside absolute path
    outside_file = tmp_path.parent / "unauthorized_outside.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(PathTraversalError):
        manager.validate_path(str(outside_file))


def test_unauthorized_root_id_fails(tmp_path: Path):
    """Verify specifying an unknown or disabled root raises UnauthorizedRootError."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path, root_id="active_root")

    with pytest.raises(UnauthorizedRootError):
        manager.validate_path("some_file.txt", root_id="non_existent_root")

    # Disable root and verify rejection
    root = manager.get_root("active_root")
    root.enabled = False
    with pytest.raises(UnauthorizedRootError):
        manager.validate_path("some_file.txt", root_id="active_root")


def test_permission_mode_read_only_blocks_writes(tmp_path: Path):
    """Verify write operations are blocked when root permission_mode is READ_ONLY."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path, root_id="read_only_root", permission_mode=PermissionMode.READ_ONLY)

    # Read succeeds
    test_file = tmp_path / "readable.txt"
    test_file.write_text("data", encoding="utf-8")
    resolved, _ = manager.validate_path("readable.txt", operation="read", must_exist=True)
    assert resolved.exists()

    # Write fails with WorkspacePermissionError
    with pytest.raises(WorkspacePermissionError, match="READ_ONLY"):
        manager.validate_path("new_file.txt", operation="write")

    with pytest.raises(WorkspacePermissionError, match="READ_ONLY"):
        manager.validate_path("readable.txt", operation="delete")


def test_permission_mode_read_write_allows_writes(tmp_path: Path):
    """Verify write operations are allowed when root permission_mode is READ_WRITE."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(
        tmp_path,
        root_id="writable_root",
        permission_mode=PermissionMode.READ_WRITE,
        allowed_operations=["read", "scan", "search", "write", "delete"],
    )

    resolved, root = manager.validate_path("new_file.txt", operation="write", must_exist=False)
    assert root.permission_mode == PermissionMode.READ_WRITE
    assert resolved.name == "new_file.txt"


def test_windows_reserved_device_names_blocked(tmp_path: Path):
    """Verify Windows reserved device names are blocked."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path)

    for name in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1", "con.txt"]:
        with pytest.raises(SecurityViolationError, match="reserved device name"):
            manager.validate_path(name)


def test_null_bytes_rejected(tmp_path: Path):
    """Verify null bytes raise SecurityViolationError."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path)

    with pytest.raises(SecurityViolationError, match="Null bytes"):
        manager.validate_path("file.txt\0.jpg")


def test_sensitive_files_blocked(tmp_path: Path):
    """Verify access to sensitive credentials and keys is blocked."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path)

    sensitive_names = [".env", ".env.local", "id_rsa", "id_rsa.pub", "id_ed25519", "server.key", "credentials.json"]
    for s_name in sensitive_names:
        with pytest.raises(SecurityViolationError, match="sensitive file"):
            manager.validate_path(s_name)


def test_symlink_escape_blocked(tmp_path: Path):
    """Verify symlinks pointing outside the workspace boundary are rejected."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path)

    outside = tmp_path.parent / "escape_target.txt"
    outside.write_text("secret outside", encoding="utf-8")
    inside_link = tmp_path / "link_escape.txt"

    try:
        os.symlink(outside, inside_link)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported or permitted on this environment")

    with pytest.raises(PathTraversalError, match="escapes"):
        manager.validate_path("link_escape.txt", must_exist=True)


def test_symlink_inside_workspace_allowed(tmp_path: Path):
    """Verify symlinks pointing inside the workspace boundary are allowed."""
    manager = WorkspacePermissionManager()
    manager.authorize_root(tmp_path)

    internal = tmp_path / "internal_data.txt"
    internal.write_text("internal", encoding="utf-8")
    inside_link = tmp_path / "link_internal.txt"

    try:
        os.symlink(internal, inside_link)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported or permitted on this environment")

    resolved, _ = manager.validate_path("link_internal.txt", must_exist=True)
    assert resolved == internal.resolve()
