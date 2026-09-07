"""Tests for XerenCore integration with Workspace Intelligence: requirements, discovery, and safety boundaries."""

from pathlib import Path

from xeren.core.runtime import XerenCore
from xeren.workspace.manager import WorkspaceManager
from xeren.workspace.schemas import PermissionMode


def test_core_determines_workspace_requirement():
    """Verify XerenCore correctly determines WorkspaceRequirement based on task semantics."""
    core = XerenCore()

    # Sales data -> requires workspace
    req_sales = core.determine_workspace_requirement("Analyze last month's sales data")
    assert req_sales is not None
    assert req_sales.requires_workspace is True
    assert "sales" in req_sales.purpose or "data" in req_sales.purpose
    assert "csv" in req_sales.preferred_types

    # Research docs -> requires workspace
    req_research = core.determine_workspace_requirement("Use my research documents to explain quantum algorithms")
    assert req_research is not None
    assert req_research.requires_workspace is True
    assert "research" in req_research.purpose
    assert "pdf" in req_research.preferred_types or "md" in req_research.preferred_types

    # Coding bug fix -> requires workspace
    req_code = core.determine_workspace_requirement("Find my project and fix the login bug")
    assert req_code is not None
    assert req_code.requires_workspace is True
    assert "codebase" in req_code.purpose
    assert "py" in req_code.preferred_types

    # Generic conversational question -> does NOT require workspace
    req_chat = core.determine_workspace_requirement("What is the capital of France?")
    assert req_chat is None


def test_core_process_goal_with_workspace_data(tmp_path: Path):
    """Verify Core executes end-to-end task workflow with workspace data."""
    core = XerenCore()
    core.add_workspace_root(tmp_path, root_id="analytics_ws")

    (tmp_path / "sales_2025.csv").write_text("month,revenue\nJan,1000\nFeb,1500\n", encoding="utf-8")

    result = core.process_goal("Analyze my sales data")
    assert result["success"] is True
    assert result["requires_workspace"] is True
    assert "sales_2025.csv" in result["selected_files"]
    assert "workspace_discovery" in result["workflow"]
    assert "data" in result["workflow"]
    assert "verification" in result["workflow"]
    assert "experience" in result["workflow"]


def test_core_safe_fallback_when_workspace_not_configured():
    """Verify safe fallback notice when workspace data is needed but no root is authorized."""
    core = XerenCore()  # No workspace roots configured

    result = core.process_goal("Analyze my sales data")
    assert result["requires_workspace"] is True
    assert result["status"] == "no_workspace_configured"
    assert result["requires_user_input"] is True
    assert "no workspace root is currently authorized" in result["response"]
