"""Unit tests for character and recursive text chunkers."""

from xeren.rag.chunkers.recursive import CharacterChunker, RecursiveTextChunker
from xeren.rag.document import Document


def test_character_chunker() -> None:
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    doc = Document.from_text(text, source="alphabet.txt", title="Alphabet")

    chunker = CharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk(doc)

    assert len(chunks) == 3
    assert chunks[0].content == "ABCDEFGHIJ"  # 0..10
    assert chunks[1].content == "IJKLMNOPQR"  # 8..18
    assert chunks[2].content == "QRSTUVWXYZ"  # 16..26
    assert chunks[0].total_chunks == 3
    assert chunks[0].metadata["source"] == "alphabet.txt"
    assert chunks[0].metadata["title"] == "Alphabet"


def test_recursive_chunker_paragraphs() -> None:
    text = (
        "Paragraph 1 contains some introductory details about the system.\n\n"
        "Paragraph 2 discusses the second major concept in depth.\n\n"
        "Paragraph 3 concludes the discussion with summary thoughts."
    )
    doc = Document.from_text(text, source="article.txt")

    chunker = RecursiveTextChunker(chunk_size=75, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 3
    for c in chunks:
        assert len(c.content) <= 100
        assert c.chunk_index >= 0
        assert c.total_chunks == len(chunks)


def test_recursive_chunker_empty_document() -> None:
    doc = Document.from_text("", source="empty.txt")
    chunker = RecursiveTextChunker()
    chunks = chunker.chunk(doc)
    assert chunks == []
