"""Tests for WorkspaceSearchIndex: fast token search, glob pattern matching, and incremental updates."""

from pathlib import Path

from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.scanner import WorkspaceScanner
from xeren.workspace.schemas import FileCategory
from xeren.workspace.search import WorkspaceSearchIndex, tokenize


def test_tokenize_normalization():
    """Verify tokenize extracts clean, lowercased alphanumeric tokens."""
    tokens = tokenize("sales_august_2025.csv")
    assert "sales" in tokens
    assert "august" in tokens
    assert "2025" in tokens
    assert "csv" in tokens


def test_search_index_keyword_and_glob(tmp_path: Path):
    """Verify search index matches tokens and wildcard glob patterns."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    (tmp_path / "sales_q1.csv").write_text("a,b\n", encoding="utf-8")
    (tmp_path / "sales_q2.csv").write_text("a,b\n", encoding="utf-8")
    (tmp_path / "marketing_report.xlsx").write_text("sheet\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('test')\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    index = WorkspaceSearchIndex()
    index.index_files(scanned)

    # Keyword search
    sales_results = index.search(query="sales")
    assert len(sales_results) == 2
    for r in sales_results:
        assert "sales" in r.name

    # Glob search
    q_results = index.search(glob_pattern="*q*.csv")
    assert len(q_results) == 2

    # Extension filter
    py_results = index.search(preferred_types=["py"])
    assert len(py_results) == 1
    assert py_results[0].name == "main.py"


def test_search_index_incremental_updates(tmp_path: Path):
    """Verify adding, updating, and removing entries from the search index."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    file_1 = tmp_path / "doc.txt"
    file_1.write_text("content", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    index = WorkspaceSearchIndex()
    index.index_files(scanned)
    assert len(index.get_all()) == 1

    # Remove
    index.remove(scanned[0].file_id)
    assert len(index.get_all()) == 0
    assert index.search(query="doc") == []

    # Re-add
    index.add_or_update(scanned[0])
    assert len(index.get_all()) == 1
    assert len(index.search(query="doc")) == 1
