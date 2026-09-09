"""Tests for WorkspaceManager: end-to-end root management, discovery, context generation, and write safety."""

from pathlib import Path
import pytest

from xeren.workspace.manager import (
    WorkspaceManager,
    WorkspacePermissionError,
)
from xeren.workspace.schemas import (
    DiscoveryRequest,
    PermissionMode,
    WorkspaceRequirement,
)


def test_manager_discover_and_build_context(tmp_path: Path):
    """Verify WorkspaceManager discovers files and builds structured WorkspaceContext."""
    manager = WorkspaceManager()
    manager.authorize_root(tmp_path, root_id="main_root")

    (tmp_path / "sales_august.csv").write_text("item,qty,price\nA,10,5.0\n", encoding="utf-8")
    (tmp_path / "sales_september.csv").write_text("item,qty,price\nB,20,5.0\n", encoding="utf-8")

    req = WorkspaceRequirement(
        purpose="sales_data_analysis",
        preferred_types=["csv"],
        query_terms=["sales", "august"],
    )

    ctx = manager.build_context(goal="Analyze sales august data", requirement=req)

    assert len(ctx.authorized_roots) == 1
    assert len(ctx.selected_resources) == 1
    assert ctx.selected_resources[0].relative_path == "sales_august.csv"
    assert "sales_august.csv" in ctx.retrieval_status
    assert ctx.ambiguity_detected is False


def test_manager_deleted_and_modified_files(tmp_path: Path):
    """Verify scanner handles file deletion and modification dynamically."""
    manager = WorkspaceManager()
    root = manager.authorize_root(tmp_path)

    f = tmp_path / "dynamic.txt"
    f.write_text("original content", encoding="utf-8")

    # First scan
    scanned_1 = manager.scan()
    assert any(s.name == "dynamic.txt" for s in scanned_1)

    # Delete file and rescan
    f.unlink()
    scanned_2 = manager.scan(force_rescan=True)
    assert not any(s.name == "dynamic.txt" for s in scanned_2)


def test_manager_write_file_enforces_permissions(tmp_path: Path):
    """Verify write_file strictly enforces READ_ONLY vs READ_WRITE."""
    manager = WorkspaceManager()
    manager.authorize_root(tmp_path, root_id="ro_root", permission_mode=PermissionMode.READ_ONLY)

    # Attempting to write on READ_ONLY root must raise WorkspacePermissionError
    with pytest.raises(WorkspacePermissionError):
        manager.write_file("new_output.txt", content="test")

    # Authorize writable root
    sub_writable = tmp_path / "writable"
    sub_writable.mkdir()
    manager.authorize_root(
        sub_writable,
        root_id="rw_root",
        permission_mode=PermissionMode.READ_WRITE,
        allowed_operations=["read", "scan", "search", "write", "delete"],
    )

    res = manager.write_file("output.txt", content="hello world", root_id="rw_root")
    assert res["success"] is True
    assert (sub_writable / "output.txt").exists()
    assert (sub_writable / "output.txt").read_text(encoding="utf-8") == "hello world"
