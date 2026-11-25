"""Unit tests for document loaders."""

import json
from pathlib import Path
import pytest

from xeren.rag.errors import DocumentLoadingError, UnsupportedFormatError
from xeren.rag.loaders.directory import DirectoryLoader
from xeren.rag.loaders.json_loader import JSONLoader
from xeren.rag.loaders.markdown import MarkdownLoader
from xeren.rag.loaders.registry import LoaderRegistry
from xeren.rag.loaders.text import TextFileLoader


def test_text_loader(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Sample plain text content", encoding="utf-8")

    loader = TextFileLoader()
    assert loader.supports(test_file) is True

    docs = loader.load(test_file)
    assert len(docs) == 1
    assert docs[0].content == "Sample plain text content"
    assert docs[0].metadata.source == str(test_file.resolve())
    assert docs[0].metadata.title == "sample"


def test_markdown_loader_with_frontmatter(tmp_path: Path) -> None:
    md_content = """---
title: "Custom Title"
author: "Xeren Team"
category: "AI"
---
# Main Heading

This is markdown body content.
"""
    md_file = tmp_path / "doc.md"
    md_file.write_text(md_content, encoding="utf-8")

    loader = MarkdownLoader()
    assert loader.supports(md_file) is True

    docs = loader.load(md_file)
    assert len(docs) == 1
    assert "This is markdown body content." in docs[0].content
    assert docs[0].metadata.title == "Custom Title"
    assert docs[0].metadata.extra["author"] == "Xeren Team"
    assert docs[0].metadata.extra["category"] == "AI"
    assert "Main Heading" in docs[0].metadata.extra["headings"]


def test_json_loader_array(tmp_path: Path) -> None:
    data = [
        {"id": 1, "text": "First entry", "author": "Alice"},
        {"id": 2, "text": "Second entry", "author": "Bob"},
    ]
    json_file = tmp_path / "records.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    loader = JSONLoader(content_key="text")
    assert loader.supports(json_file) is True

    docs = loader.load(json_file)
    assert len(docs) == 2
    assert docs[0].content == "First entry"
    assert docs[0].metadata.extra["record_index"] == 0
    assert docs[1].content == "Second entry"
    assert docs[1].metadata.extra["record_index"] == 1


def test_jsonl_loader(tmp_path: Path) -> None:
    lines = [
        json.dumps({"text": "Line 1 item"}),
        json.dumps({"text": "Line 2 item"}),
    ]
    jsonl_file = tmp_path / "stream.jsonl"
    jsonl_file.write_text("\n".join(lines), encoding="utf-8")

    loader = JSONLoader()
    docs = loader.load(jsonl_file)
    assert len(docs) == 2
    assert docs[0].content == "Line 1 item"
    assert docs[1].content == "Line 2 item"


def test_loader_registry_dispatch(tmp_path: Path) -> None:
    registry = LoaderRegistry()
    txt_file = tmp_path / "a.txt"
    txt_file.write_text("text", encoding="utf-8")
    md_file = tmp_path / "b.md"
    md_file.write_text("# md", encoding="utf-8")
    json_file = tmp_path / "c.json"
    json_file.write_text("{}", encoding="utf-8")

    assert isinstance(registry.get_loader_for(txt_file), TextFileLoader)
    assert isinstance(registry.get_loader_for(md_file), MarkdownLoader)
    assert isinstance(registry.get_loader_for(json_file), JSONLoader)

    with pytest.raises(UnsupportedFormatError):
        registry.get_loader_for(tmp_path / "unknown.xyz123")


def test_directory_loader(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "file1.txt").write_text("Doc 1", encoding="utf-8")
    (tmp_path / "sub" / "file2.md").write_text("# Doc 2", encoding="utf-8")
    (tmp_path / "ignored.bin").write_bytes(b"\x00\x01\x02")

    dir_loader = DirectoryLoader()
    assert dir_loader.supports(tmp_path) is True

    docs = dir_loader.load(tmp_path)
    assert len(docs) == 2
    contents = {d.content for d in docs}
    assert "Doc 1" in contents
    assert "# Doc 2" in contents
