"""Integration tests for IngestionPipeline."""

from pathlib import Path
import pytest

from xeren.rag.chunkers.recursive import RecursiveTextChunker
from xeren.rag.document import Document
from xeren.rag.normalizers.text_normalizer import TextNormalizer
from xeren.rag.pipeline import IngestionPipeline


def test_pipeline_process_text() -> None:
    pipeline = IngestionPipeline()
    text = "Line 1.\r\n\r\nLine 2.\r\n\r\nLine 3."
    chunks = pipeline.process_text(text, source="memory", title="Demo")

    assert len(chunks) >= 1
    assert chunks[0].metadata["source"] == "memory"
    assert chunks[0].metadata["title"] == "Demo"
    assert "\r" not in chunks[0].content


@pytest.mark.asyncio
async def test_pipeline_aprocess_text() -> None:
    pipeline = IngestionPipeline()
    text = "Async text ingestion test."
    chunks = await pipeline.aprocess_text(text, source="async_src")

    assert len(chunks) == 1
    assert chunks[0].content == "Async text ingestion test."


def test_pipeline_process_file(tmp_path: Path) -> None:
    pipeline = IngestionPipeline()
    doc_path = tmp_path / "guide.md"
    doc_path.write_text(
        "---\ntitle: Guide\n---\n# Chapter 1\n\nContent for chapter 1 goes here.\n",
        encoding="utf-8",
    )

    chunks = pipeline.process_file(doc_path)
    assert len(chunks) >= 1
    assert chunks[0].metadata["title"] == "Guide"
    assert "Content for chapter 1 goes here." in chunks[0].content


def test_pipeline_process_directory(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "doc1.txt").write_text("Hello text file 1", encoding="utf-8")
    (tmp_path / "sub" / "doc2.md").write_text("# Hello markdown file 2", encoding="utf-8")

    pipeline = IngestionPipeline()
    chunks = pipeline.process_directory(tmp_path)

    assert len(chunks) == 2
    contents = {c.content for c in chunks}
    assert any("Hello text file 1" in c for c in contents)
    assert any("# Hello markdown file 2" in c for c in contents)
