"""Tests for FileReaderTool: UTF-8 decoding, line range slicing, safe binary detection, and secret redaction."""

import pytest

from xeren.plugins.file.tools.reader import FileReaderTool
from xeren.plugins.file.tools.security import FileSecurityTool, FileSizeLimitError


def test_read_normal_text_file(tmp_path):
    """Verify clean full file reading and relative path reporting."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reader = FileReaderTool(security_tool=security)

    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello, Xeren!", encoding="utf-8")

    res = reader.read_file("sample.txt")
    assert res["success"] is True
    assert res["content"] == "Hello, Xeren!"
    assert res["is_binary"] is False
    assert res["bytes_read"] > 0
    assert res["warning"] is None


def test_read_line_range_slicing(tmp_path):
    """Verify line_start and line_end partial reading."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reader = FileReaderTool(security_tool=security)

    file_path = tmp_path / "lines.txt"
    lines = [f"Line {i}\n" for i in range(1, 11)]
    file_path.write_text("".join(lines), encoding="utf-8")

    # Read lines 3 through 5
    res = reader.read_file("lines.txt", line_start=3, line_end=5)
    assert res["success"] is True
    assert res["content"] == "Line 3\nLine 4\nLine 5\n"

    # Read from line 8 to end
    res_end = reader.read_file("lines.txt", line_start=8)
    assert res_end["content"] == "Line 8\nLine 9\nLine 10\n"


def test_safe_binary_file_handling(tmp_path):
    """Verify binary files are detected, metadata is reported, and raw binary is NOT decoded as text."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reader = FileReaderTool(security_tool=security)

    bin_file = tmp_path / "image.png"
    # Write arbitrary binary bytes containing null bytes
    binary_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00"
    bin_file.write_bytes(binary_bytes)

    res = reader.read_file("image.png")
    assert res["success"] is True
    assert res["is_binary"] is True
    # Crucial: content must be None, NOT raw binary text
    assert res["content"] is None
    assert res["warning"] is not None
    assert "Binary file detected" in res["warning"]
    assert res["bytes_read"] == len(binary_bytes)


def test_read_size_limit_exceeded(tmp_path):
    """Verify reading a file exceeding max_size_bytes raises FileSizeLimitError."""
    security = FileSecurityTool(workspace_dir=tmp_path, max_file_size_bytes=50)
    reader = FileReaderTool(security_tool=security)

    large_file = tmp_path / "large.txt"
    large_file.write_text("A" * 200, encoding="utf-8")

    with pytest.raises(FileSizeLimitError):
        reader.read_file("large.txt")


def test_read_nonexistent_file_and_directory(tmp_path):
    """Verify reading missing files or directories raises appropriate errors."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reader = FileReaderTool(security_tool=security)

    # Missing file
    with pytest.raises(FileNotFoundError):
        reader.read_file("missing.txt")

    # Directory
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(IsADirectoryError):
        reader.read_file("sub")


def test_read_secret_redaction_toggle(tmp_path):
    """Verify secret redaction can be toggled via redaction_enabled."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    reader = FileReaderTool(security_tool=security)

    cred_file = tmp_path / "keys.env"
    cred_file.write_text("SECRET_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz", encoding="utf-8")

    # Redaction enabled (default)
    res_redacted = reader.read_file("keys.env", redaction_enabled=True)
    assert res_redacted["redacted_secrets"] is True
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in res_redacted["content"]

    # Redaction disabled
    res_raw = reader.read_file("keys.env", redaction_enabled=False)
    assert res_raw["redacted_secrets"] is False
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" in res_raw["content"]
