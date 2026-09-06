"""Tests for FileManagerTool: delete, move, copy, listing, metadata, and dry-run mode."""

from pathlib import Path
import pytest

from xeren.plugins.file.tools.manager import FileManagerTool
from xeren.plugins.file.tools.security import FileSecurityError, FileSecurityTool


def test_delete_file_and_directory(tmp_path):
    """Verify file and recursive directory deletion."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    # 1. Delete file
    target_file = tmp_path / "delete_me.txt"
    target_file.write_text("temp", encoding="utf-8")
    res_file = manager.delete_entity("delete_me.txt")
    assert res_file["success"] is True
    assert not target_file.exists()

    # 2. Delete recursive directory
    sub = tmp_path / "sub_dir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested", encoding="utf-8")
    res_dir = manager.delete_entity("sub_dir", recursive=True)
    assert res_dir["success"] is True
    assert not sub.exists()


def test_delete_workspace_root_blocked(tmp_path):
    """Verify deletion of the approved workspace root is strictly blocked."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    with pytest.raises(FileSecurityError, match="workspace root"):
        manager.delete_entity(".")


def test_delete_dry_run(tmp_path):
    """Verify dry-run delete reports action without deleting file."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    target = tmp_path / "keep_me.txt"
    target.write_text("safe", encoding="utf-8")

    res = manager.delete_entity("keep_me.txt", dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert target.exists()


def test_move_and_copy_entities(tmp_path):
    """Verify move and copy within workspace boundaries with overwrite protection."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    src = tmp_path / "source.txt"
    src.write_text("source data", encoding="utf-8")

    # 1. Copy
    res_copy = manager.copy_entity("source.txt", "copy.txt")
    assert res_copy["success"] is True
    assert (tmp_path / "copy.txt").read_text(encoding="utf-8") == "source data"
    assert src.exists()

    # Copy overwrite protection
    with pytest.raises(FileExistsError):
        manager.copy_entity("source.txt", "copy.txt", overwrite=False)

    # 2. Move
    res_move = manager.move_entity("source.txt", "moved.txt")
    assert res_move["success"] is True
    assert not src.exists()
    assert (tmp_path / "moved.txt").read_text(encoding="utf-8") == "source data"


def test_move_and_copy_dry_run(tmp_path):
    """Verify dry_run=True does not alter filesystem for move and copy."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    src = tmp_path / "dry_src.txt"
    src.write_text("dry data", encoding="utf-8")

    # Dry run move
    res_move = manager.move_entity("dry_src.txt", "dry_dst.txt", dry_run=True)
    assert res_move["success"] is True
    assert res_move["dry_run"] is True
    assert src.exists()
    assert not (tmp_path / "dry_dst.txt").exists()

    # Dry run copy
    res_copy = manager.copy_entity("dry_src.txt", "dry_dst_copy.txt", dry_run=True)
    assert res_copy["success"] is True
    assert res_copy["dry_run"] is True
    assert not (tmp_path / "dry_dst_copy.txt").exists()


def test_list_directory_filters(tmp_path):
    """Verify listing with recursion, patterns, hidden files, and max_results."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    (tmp_path / "a.py").write_text("a = 1", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b = 2", encoding="utf-8")
    (tmp_path / ".hidden.py").write_text("hidden", encoding="utf-8")

    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "c.py").write_text("c = 3", encoding="utf-8")

    # 1. Pattern filter *.py
    py_items = manager.list_directory(pattern="*.py", recursive=True, include_hidden=False)
    py_paths = {item.path for item in py_items}
    assert "a.py" in py_paths
    assert "pkg/c.py" in py_paths or "pkg\\c.py" in py_paths or (tmp_path / "pkg" / "c.py").name in [p.split("/")[-1] for p in py_paths]
    assert "b.txt" not in py_paths
    assert ".hidden.py" not in py_paths

    # 2. Include hidden
    hidden_items = manager.list_directory(pattern="*.py", recursive=False, include_hidden=True)
    hidden_names = [item.name for item in hidden_items]
    assert ".hidden.py" in hidden_names

    # 3. Max results
    limited = manager.list_directory(max_results=1)
    assert len(limited) == 1


def test_get_metadata_inspection(tmp_path):
    """Verify metadata inspection returns size, checksum, and file attributes."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    manager = FileManagerTool(security_tool=security)

    target = tmp_path / "data.json"
    target.write_text('{"status": "ok"}', encoding="utf-8")

    meta = manager.get_metadata("data.json")
    assert meta.name == "data.json"
    assert meta.is_file is True
    assert meta.is_directory is False
    assert meta.size_bytes == len('{"status": "ok"}'.encode("utf-8"))
    assert meta.extension == ".json"
    assert meta.checksum_sha256 is not None
    assert meta.is_binary is False
