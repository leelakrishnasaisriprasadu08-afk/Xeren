"""End-to-end provenance preservation tests for RAG pipeline and embeddings."""

from pathlib import Path

from xeren.rag.chunkers.markdown_header import MarkdownHeaderChunker
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.loaders.markdown import MarkdownLoader
from xeren.rag.normalizers.text_normalizer import TextNormalizer


def test_end_to_end_provenance_preservation(tmp_path: Path) -> None:
    doc_content = """---
title: "Architecture Specification"
version: "1.0"
author: "Xeren Core Team"
---
# System Design

Core system architecture specifications.

## Memory Subsystem

Details regarding episodic and working memory.

### Working Memory

Buffer mechanisms and scratchpad lifecycle.
"""
    file_path = tmp_path / "architecture.md"
    file_path.write_text(doc_content, encoding="utf-8")

    # 1. Load document
    loader = MarkdownLoader()
    documents = loader.load(file_path)
    assert len(documents) == 1
    doc = documents[0]

    assert doc.metadata.source == str(file_path.resolve())
    assert doc.metadata.title == "Architecture Specification"
    assert doc.metadata.extra["author"] == "Xeren Core Team"
    assert doc.metadata.extra["version"] == "1.0"

    # 2. Normalize
    normalizer = TextNormalizer()
    normalized_doc = normalizer.normalize(doc)
    assert normalized_doc.metadata.source == str(file_path.resolve())

    # 3. Chunk with Header Hierarchy
    chunker = MarkdownHeaderChunker(max_chunk_size=1000)
    chunks = chunker.chunk(normalized_doc)
    assert len(chunks) == 3

    working_mem_chunk = next(c for c in chunks if "Buffer mechanisms" in c.content)
    assert working_mem_chunk.document_id == doc.id
    assert working_mem_chunk.metadata["source"] == str(file_path.resolve())
    assert working_mem_chunk.metadata["title"] == "Architecture Specification"
    assert working_mem_chunk.metadata["author"] == "Xeren Core Team"
    assert working_mem_chunk.metadata["header_path"] == "System Design > Memory Subsystem > Working Memory"
    assert working_mem_chunk.metadata["current_header"] == "Working Memory"
    assert working_mem_chunk.start_char_index is not None
    assert working_mem_chunk.end_char_index is not None
    assert working_mem_chunk.checksum is not None

    # 4. Embed Chunks
    embedder = MockEmbeddingModel(dimension=64)
    embedded_chunks = embedder.embed_chunks(chunks)
    assert len(embedded_chunks) == 3

    embedded_working_mem = next(
        ec for ec in embedded_chunks if "Buffer mechanisms" in ec.chunk.content
    )
    # Validate that original chunk provenance is completely intact
    assert embedded_working_mem.chunk.document_id == doc.id
    assert embedded_working_mem.chunk.metadata["source"] == str(file_path.resolve())
    assert embedded_working_mem.chunk.metadata["header_path"] == "System Design > Memory Subsystem > Working Memory"
    assert len(embedded_working_mem.embedding) == 64
    assert embedded_working_mem.embedding_model == "mock-embed"
