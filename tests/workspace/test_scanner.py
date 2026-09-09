"""Tests for WorkspaceScanner: metadata extraction, categorisation, caching, and exclusion of noise."""

from pathlib import Path

from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.scanner import WorkspaceScanner
from xeren.workspace.schemas import FileCategory


def test_scanner_extracts_lightweight_metadata(tmp_path: Path):
    """Verify scanner extracts structural metadata without loading entire contents."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path, root_id="main")

    # Create various sample files
    (tmp_path / "sales.csv").write_text("id,amount\n1,500\n", encoding="utf-8")
    (tmp_path / "report.md").write_text("# Monthly Report\nDetails here.\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def run():\n    pass\n", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    assert len(scanned) == 3
    by_name = {s.name: s for s in scanned}

    # Verify CSV metadata
    csv_meta = by_name["sales.csv"]
    assert csv_meta.extension == ".csv"
    assert csv_meta.category == FileCategory.STRUCTURED_DATA
    assert csv_meta.size_bytes > 0
    assert csv_meta.is_binary is False
    assert csv_meta.root_id == "main"

    # Verify Markdown metadata
    md_meta = by_name["report.md"]
    assert md_meta.extension == ".md"
    assert md_meta.category == FileCategory.DOCUMENT

    # Verify Python code metadata
    py_meta = by_name["app.py"]
    assert py_meta.extension == ".py"
    assert py_meta.category == FileCategory.SOURCE_CODE


def test_scanner_ignores_noise_and_hidden_directories(tmp_path: Path):
    """Verify .git, __pycache__, node_modules, and .venv are skipped."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    # Legitimate file
    (tmp_path / "important.txt").write_text("content", encoding="utf-8")

    # Noise directories
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config", encoding="utf-8")

    pycache_dir = tmp_path / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "module.cpython-311.pyc").write_bytes(b"\x00\x01\x02")

    node_modules = tmp_path / "node_modules" / "pkg"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("console.log('hi');", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scanned = scanner.scan_root(root)

    scanned_names = [s.name for s in scanned]
    assert "important.txt" in scanned_names
    assert "config" not in scanned_names
    assert "module.cpython-311.pyc" not in scanned_names
    assert "index.js" not in scanned_names


def test_scanner_caching_and_invalidation(tmp_path: Path):
    """Verify scanner caching prevents redundant re-computation when files are unchanged."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path, root_id="cached_root")

    file_a = tmp_path / "file_a.txt"
    file_a.write_text("version 1", encoding="utf-8")

    scanner = WorkspaceScanner(permission_manager=manager)
    scan_1 = scanner.scan_root(root)
    assert len(scan_1) == 1

    # Second scan returns cached metadata instance
    scan_2 = scanner.scan_root(root)
    assert scan_1[0] is scan_2[0]

    # Invalidate cache
    scanner.invalidate_cache(root_id="cached_root")
    scan_3 = scanner.scan_root(root)
    assert len(scan_3) == 1
    assert scan_3[0].name == "file_a.txt"
