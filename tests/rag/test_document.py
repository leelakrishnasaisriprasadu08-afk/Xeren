"""Unit tests for Document, DocumentChunk, and DocumentMetadata."""

from xeren.rag.document import Document, DocumentChunk, DocumentMetadata


def test_document_metadata_defaults() -> None:
    meta = DocumentMetadata(source="test.txt", title="Test")
    assert meta.source == "test.txt"
    assert meta.title == "Test"
    assert meta.created_at is not None
    assert meta.extra == {}


def test_document_from_text() -> None:
    text = "Hello Xeren RAG"
    doc = Document.from_text(text, source="memory_buffer", title="Doc1", extra={"tag": "demo"})
    assert doc.content == text
    assert doc.metadata.source == "memory_buffer"
    assert doc.metadata.title == "Doc1"
    assert doc.metadata.extra["tag"] == "demo"
    assert doc.metadata.checksum is not None
    assert doc.metadata.file_size == len(text.encode("utf-8"))


def test_document_chunk_properties() -> None:
    chunk = DocumentChunk(
        document_id="doc-123",
        content="Chunk piece",
        chunk_index=0,
        total_chunks=1,
    )
    assert chunk.document_id == "doc-123"
    assert chunk.content == "Chunk piece"
    assert chunk.character_count == len("Chunk piece")
    assert chunk.token_count is not None and chunk.token_count > 0
    assert chunk.checksum is not None and len(chunk.checksum) == 64
