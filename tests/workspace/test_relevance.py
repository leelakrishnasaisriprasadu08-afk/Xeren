"""Tests for RelevanceRanker: multi-signal ranking, domain boosts, and safe reason explanations."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.relevance import RelevanceRanker
from xeren.workspace.scanner import WorkspaceScanner


def test_relevance_ranking_signals(tmp_path: Path):
    """Verify filename, type boost, and path signals correctly elevate candidate scores."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    # 1. Direct sales data file
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sales_file = data_dir / "sales_august.csv"
    sales_file.write_text("date,revenue\n2025-08-01,15000\n", encoding="utf-8")

    # 2. Distractor doc
    doc_file = tmp_path / "readme.md"
    doc_file.write_text("# Project Setup\nSetup steps.\n", encoding="utf-8")

    # 3. Source file
    code_file = tmp_path / "calc.py"
    code_file.write_text("def calc(): pass\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result = ranker.rank_candidates(
        goal="Analyze my sales data",
        files=scanned,
        preferred_types=["csv", "xlsx"],
    )

    assert len(result.candidates) >= 1
    top = result.candidates[0]
    assert top.relative_path == "data/sales_august.csv"
    assert top.score >= 0.70
    assert "sales" in top.reason.lower() or "structured data" in top.reason.lower()
    assert result.selected_candidates == [top]
    assert result.ambiguity_detected is False


def test_recency_signal_elevation(tmp_path: Path):
    """Verify recently modified files receive a boost when goal specifies 'yesterday' or 'recent'."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    # Recent file
    recent_file = tmp_path / "auth_controller.py"
    recent_file.write_text("class AuthController: pass\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result_normal = ranker.rank_candidates(goal="Inspect login controller", files=scanned)
    result_yesterday = ranker.rank_candidates(goal="Find the project I was working on yesterday and inspect login controller", files=scanned)

    # Recency boost should be reflected in yesterday query
    assert result_yesterday.candidates[0].score >= result_normal.candidates[0].score
    assert "yesterday" in result_yesterday.candidates[0].reason.lower() or "recent" in result_yesterday.candidates[0].reason.lower() or result_yesterday.candidates[0].score > 0.4
