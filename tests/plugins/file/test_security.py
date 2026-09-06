"""Tests for FileSecurityTool: workspace boundary, traversal attacks, symlinks, size limits, and secret redaction."""

import os
from pathlib import Path
import pytest

from xeren.plugins.file.tools.security import (
    FileSecurityError,
    FileSecurityTool,
    FileSizeLimitError,
    PathTraversalError,
)


def test_workspace_boundary_valid_paths(tmp_path):
    """Verify legitimate paths and subdirectories inside workspace resolve cleanly."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    sub = tmp_path / "subdir" / "nested"
    sub.mkdir(parents=True)
    target_file = sub / "doc.txt"
    target_file.write_text("content", encoding="utf-8")

    # Relative path
    resolved_rel = security.resolve_and_validate_path("subdir/nested/doc.txt", must_exist=True)
    assert resolved_rel == target_file.resolve()

    # Relative path to root
    resolved_root = security.resolve_and_validate_path(".", must_exist=True)
    assert resolved_root == tmp_path.resolve()

    # Absolute path inside workspace
    resolved_abs = security.resolve_and_validate_path(str(target_file), must_exist=True)
    assert resolved_abs == target_file.resolve()


def test_path_traversal_attempts_blocked(tmp_path):
    """Verify directory traversal escapes are rejected."""
    security = FileSecurityTool(workspace_dir=tmp_path)

    # Standard traversal escape
    with pytest.raises(PathTraversalError):
        security.resolve_and_validate_path("../../outside.txt")

    # Windows style traversal
    with pytest.raises(PathTraversalError):
        security.resolve_and_validate_path("..\\..\\outside.txt")

    # Parent directory escape
    outside_dir = tmp_path.parent / "sibling_dir" / "secret.txt"
    with pytest.raises(PathTraversalError):
        security.resolve_and_validate_path(str(outside_dir))


def test_null_bytes_and_empty_paths_rejected(tmp_path):
    """Verify null bytes and empty inputs raise security errors."""
    security = FileSecurityTool(workspace_dir=tmp_path)

    with pytest.raises(PathTraversalError):
        security.resolve_and_validate_path("")

    with pytest.raises(FileSecurityError, match="Null bytes"):
        security.resolve_and_validate_path("file.txt\0.jpg")


def test_windows_reserved_device_names_rejected(tmp_path):
    """Verify Windows reserved device names are blocked."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reserved_names = ["CON", "prn", "AUX", "nul", "com1", "lpt1", "con.txt"]

    for name in reserved_names:
        with pytest.raises(FileSecurityError, match="reserved system device name"):
            security.resolve_and_validate_path(name)


def test_symlink_escape_blocked(tmp_path):
    """Verify symlinks pointing outside the workspace boundary are rejected."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    outside_file = tmp_path.parent / "external_target.txt"
    outside_file.write_text("external secret", encoding="utf-8")

    link_inside = tmp_path / "link_to_outside.txt"
    try:
        os.symlink(outside_file, link_inside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported or permitted on this platform/user")

    with pytest.raises(PathTraversalError, match="escapes"):
        security.resolve_and_validate_path("link_to_outside.txt", must_exist=True)


def test_symlink_inside_workspace_permitted(tmp_path):
    """Verify symlinks resolving strictly within workspace are permitted."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    internal_file = tmp_path / "internal.txt"
    internal_file.write_text("internal content", encoding="utf-8")

    internal_link = tmp_path / "link_to_internal.txt"
    try:
        os.symlink(internal_file, internal_link)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported or permitted on this platform/user")

    resolved = security.resolve_and_validate_path("link_to_internal.txt", must_exist=True)
    assert resolved == internal_file.resolve()


def test_prevent_workspace_root_destructive_action(tmp_path):
    """Verify that destructive operations against the workspace root are blocked."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    with pytest.raises(FileSecurityError, match="Cannot perform destructive operation"):
        security.validate_not_workspace_root(tmp_path, operation_name="delete")


def test_file_size_limit_enforcement(tmp_path):
    """Verify file size limit checks."""
    security = FileSecurityTool(workspace_dir=tmp_path, max_file_size_bytes=1000)

    # Below limit succeeds
    security.validate_size(500)

    # Exceeding limit fails
    with pytest.raises(FileSizeLimitError, match="exceeds"):
        security.validate_size(1001)

    # Override limit succeeds
    security.validate_size(1500, limit_override=2000)


def test_best_effort_secret_redaction(tmp_path):
    """Verify best-effort secret redaction masks keys and credentials without raw logging."""
    security = FileSecurityTool(workspace_dir=tmp_path, redaction_enabled=True)

    text_with_keys = (
        "Config: api_key='secret_pass123', token=sk-abcdefghijklmnopqrstuvwxyz123456\n"
        "AWS: AKIAIOSFODNN7EXAMPLE\n"
        "GitHub: ghp_123456789012345678901234567890123456\n"
        "Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDcSemACt8x4iTMCda8Yhe3iZaWbvV5XKSTbuAn0M"
    )

    redacted_text, occurred = security.redact_secrets_if_enabled(text_with_keys)
    assert occurred is True
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in (redacted_text or "")
    assert "AKIAIOSFODNN7EXAMPLE" not in (redacted_text or "")
    assert "ghp_123456789012345678901234567890123456" not in (redacted_text or "")
    assert "[REDACTED" in (redacted_text or "")

    # When redaction is disabled
    unredacted, was_redacted = security.redact_secrets_if_enabled(text_with_keys, enabled=False)
    assert was_redacted is False
    assert unredacted == text_with_keys

    # When no secrets exist
    clean_text = "Hello world, this is a clean file without secrets."
    clean_res, clean_occurred = security.redact_secrets_if_enabled(clean_text)
    assert clean_occurred is False
    assert clean_res == clean_text
