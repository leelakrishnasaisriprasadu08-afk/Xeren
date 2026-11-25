"""Tests for FileSearchTool: pattern matching, content regex/text search, binary skipping, and noise directory exclusion."""

from pathlib import Path
import pytest

from xeren.plugins.file.tools.search import FileSearchTool
from xeren.plugins.file.tools.security import FileSecurityTool


def test_search_filename_pattern(tmp_path):
    """Verify filename glob pattern matching."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    search_tool = FileSearchTool(security_tool=security)

    (tmp_path / "module_a.py").write_text("# Python a", encoding="utf-8")
    (tmp_path / "module_b.py").write_text("# Python b", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# Markdown", encoding="utf-8")

    matches = search_tool.search(pattern="*.py")
    matched_paths = [m.path for m in matches]
    assert len(matches) == 2
    assert any("module_a.py" in p for p in matched_paths)
    assert any("module_b.py" in p for p in matched_paths)
    assert not any("readme.md" in p for p in matched_paths)


def test_search_content_text_and_regex(tmp_path):
    """Verify line-by-line text and regex matching with line numbers."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    search_tool = FileSearchTool(security_tool=security)

    f1 = tmp_path / "code.py"
    f1.write_text("line 1\ndef process_data():\n    pass\n", encoding="utf-8")

    f2 = tmp_path / "other.py"
    f2.write_text("def process_items():\n    return True\n", encoding="utf-8")

    # 1. Literal search
    lit_matches = search_tool.search(pattern="*.py", search_content="process_data")
    assert len(lit_matches) == 1
    assert lit_matches[0].line_number == 2
    assert "def process_data():" in (lit_matches[0].line_content or "")

    # 2. Regex search
    regex_matches = search_tool.search(pattern="*.py", search_content=r"def process_\w+", is_regex=True)
    assert len(regex_matches) == 2


def test_search_skips_binary_files(tmp_path):
    """Verify content search skips binary files and does not throw decoding errors."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    search_tool = FileSearchTool(security_tool=security)

    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"some text with \x00 null byte and secret_key")

    text_file = tmp_path / "data.txt"
    text_file.write_text("some text with secret_key", encoding="utf-8")

    matches = search_tool.search(search_content="secret_key")
    # Only text_file should match; data.bin must be skipped
    assert len(matches) == 1
    assert "data.txt" in matches[0].path


def test_search_excludes_default_noise_directories(tmp_path):
    """Verify searches automatically skip .git, .venv, and node_modules folders."""
    security = FileSecurityTool(workspace_dir=tmp_path)
    search_tool = FileSearchTool(security_tool=security)

    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "target.py").write_text("match_me", encoding="utf-8")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "target.py").write_text("match_me", encoding="utf-8")

    matches = search_tool.search(search_content="match_me")
    assert len(matches) == 1
    assert "src" in matches[0].path
    assert ".venv" not in matches[0].path


def test_search_has_no_rag_or_embeddings_dependency():
    """Verify FileSearchTool does not depend on or instantiate any vector store, embeddings, or RAG engine."""
    security = FileSecurityTool()
    search_tool = FileSearchTool(security_tool=security)

    # Ensure pure filesystem search
    assert not hasattr(search_tool, "embeddings")
    assert not hasattr(search_tool, "vector_store")
    assert not hasattr(search_tool, "chunker")
    assert not hasattr(search_tool, "llm")
