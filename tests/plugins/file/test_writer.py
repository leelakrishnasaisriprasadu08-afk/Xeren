"""Tests for FileWriterTool: atomic writes, create, modify, overwrite controls, and dry-run mode."""

from pathlib import Path
import pytest

from xeren.plugins.file.tools.security import FileSecurityTool, FileSizeLimitError
from xeren.plugins.file.tools.writer import FileWriterTool


def test_create_file_success_and_parents(tmp_path):
    """Verify creating a new file with parent directories."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    writer = FileWriterTool(security_tool=security)

    res = writer.create_file("nested/dir/new.txt", content="Hello", create_parents=True)
    assert res["success"] is True
    assert res["dry_run"] is False
    assert (tmp_path / "nested" / "dir" / "new.txt").exists()
    assert (tmp_path / "nested" / "dir" / "new.txt").read_text(encoding="utf-8") == "Hello"


def test_create_file_overwrite_protection(tmp_path):
    """Verify create_file fails if file exists unless overwrite=True."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    writer = FileWriterTool(security_tool=security)

    target = tmp_path / "existing.txt"
    target.write_text("initial", encoding="utf-8")

    # Fails when overwrite=False
    with pytest.raises(FileExistsError):
        writer.create_file("existing.txt", content="new", overwrite=False)

    assert target.read_text(encoding="utf-8") == "initial"

    # Succeeds when overwrite=True
    res = writer.create_file("existing.txt", content="overwritten", overwrite=True)
    assert res["success"] is True
    assert target.read_text(encoding="utf-8") == "overwritten"


def test_write_file_atomic(tmp_path):
    """Verify atomic write replaces content and returns valid checksum."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    writer = FileWriterTool(security_tool=security)

    res = writer.write_file("atomic.txt", content="AlphaBetaGamma", atomic=True)
    assert res["success"] is True
    assert res["bytes_written"] == len("AlphaBetaGamma".encode("utf-8"))
    assert res["checksum_sha256"] is not None

    written_path = tmp_path / "atomic.txt"
    assert written_path.read_text(encoding="utf-8") == "AlphaBetaGamma"


def test_modify_file_substring_and_lines(tmp_path):
    """Verify modify_file targeted replacement, line slicing, and error on missing target."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    writer = FileWriterTool(security_tool=security)

    f = tmp_path / "code.py"
    f.write_text("def hello():\n    return 'old'\n", encoding="utf-8")

    # 1. Substring replacement
    res_sub = writer.modify_file("code.py", target_content="'old'", replacement="'new'")
    assert res_sub["success"] is True
    assert f.read_text(encoding="utf-8") == "def hello():\n    return 'new'\n"

    # 2. Error on missing target content
    with pytest.raises(ValueError, match="not found"):
        writer.modify_file("code.py", target_content="nonexistent")

    # 3. Line range replacement
    res_lines = writer.modify_file("code.py", line_start=2, line_end=3, replacement="    return 'updated'\n")
    assert res_lines["success"] is True
    assert f.read_text(encoding="utf-8") == "def hello():\n    return 'updated'\n"


def test_write_size_limit_exceeded(tmp_path):
    """Verify writing content larger than max size ceiling raises FileSizeLimitError."""
    security = FileSecurityTool(workspace_dir=tmp_path, max_file_size_bytes=100)
    writer = FileWriterTool(security_tool=security)

    large_content = "Z" * 500
    with pytest.raises(FileSizeLimitError):
        writer.write_file("too_large.txt", content=large_content)

    assert not (tmp_path / "too_large.txt").exists()


def test_dry_run_writer_operations(tmp_path):
    """Verify dry_run=True calculates outcome without modifying the filesystem."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    writer = FileWriterTool(security_tool=security)

    # 1. Dry-run create
    res_create = writer.create_file("dry_create.txt", content="Created?", dry_run=True)
    assert res_create["success"] is True
    assert res_create["dry_run"] is True
    assert not (tmp_path / "dry_create.txt").exists()

    # 2. Dry-run write on existing file
    existing = tmp_path / "dry_existing.txt"
    existing.write_text("original content", encoding="utf-8")

    res_write = writer.write_file("dry_existing.txt", content="new content", dry_run=True)
    assert res_write["success"] is True
    assert res_write["dry_run"] is True
    # Disk content must remain untouched
    assert existing.read_text(encoding="utf-8") == "original content"

    # 3. Dry-run modify
    res_mod = writer.modify_file("dry_existing.txt", target_content="original", replacement="modified", dry_run=True)
    assert res_mod["success"] is True
    assert res_mod["dry_run"] is True
    assert existing.read_text(encoding="utf-8") == "original content"
