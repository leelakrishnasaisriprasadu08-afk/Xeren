"""Tests for ambiguity handling, clarification triggers, and zero-hallucination behavior."""

from pathlib import Path

from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.relevance import RelevanceRanker
from xeren.workspace.scanner import WorkspaceScanner


def test_single_clear_match_auto_selection(tmp_path: Path):
    """Verify single dominant candidate is automatically chosen without asking user."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    (tmp_path / "sales_report.csv").write_text("id,val\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("meeting notes\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result = ranker.rank_candidates(goal="Analyze last month's sales report", files=scanned)

    assert result.ambiguity_detected is False
    assert len(result.selected_candidates) == 1
    assert result.selected_candidates[0].relative_path == "sales_report.csv"
    assert result.clarification_message is None


def test_equally_relevant_files_trigger_clarification(tmp_path: Path):
    """Verify multiple near-identical candidates trigger a clarification question."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    (tmp_path / "sales_2025.csv").write_text("id,val\n", encoding="utf-8")
    (tmp_path / "sales_2026.csv").write_text("id,val\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result = ranker.rank_candidates(goal="Analyze sales data", files=scanned)

    assert result.ambiguity_detected is True
    assert result.clarification_message is not None
    assert "sales_2025.csv" in result.clarification_message
    assert "sales_2026.csv" in result.clarification_message
    assert "Which one" in result.clarification_message


def test_no_relevant_file_returns_clear_factual_notice(tmp_path: Path):
    """Verify missing file triggers clear notice without hallucination."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    (tmp_path / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result = ranker.rank_candidates(goal="Analyze medical genomic sequencing records", files=scanned)

    assert len(result.selected_candidates) == 0
    assert result.clarification_message is not None
    assert "no relevant files found" in result.clarification_message.lower() or "no strongly matching" in result.clarification_message.lower()


def test_multi_file_goal_selects_all_relevant_files(tmp_path: Path):
    """Verify multi-file requests ('Use my research papers and project requirements') return both candidates."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "paper1.md").write_text("# Research Paper 1\nQuantum algorithms.\n", encoding="utf-8")
    (docs_dir / "paper2.md").write_text("# Research Paper 2\nQuantum error correction.\n", encoding="utf-8")
    (tmp_path / "requirements.md").write_text("# Project Requirements\nBuild prototype.\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    ranker = RelevanceRanker()
    result = ranker.rank_candidates(
        goal="Use my research papers and project requirements to build the prototype",
        files=scanned,
    )

    selected_paths = [c.relative_path for c in result.selected_candidates]
    assert len(result.selected_candidates) >= 2
    assert any("paper" in p for p in selected_paths)
    assert any("requirements" in p for p in selected_paths)
