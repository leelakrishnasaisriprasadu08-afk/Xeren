"""Unit tests for MarkdownHeaderChunker."""

from xeren.rag.chunkers.markdown_header import MarkdownHeaderChunker
from xeren.rag.document import Document


def test_markdown_header_chunker_hierarchy() -> None:
    md_text = """# Machine Learning

Overview of ML.

## Supervised Learning

Description of supervised learning algorithms.

### Regression

Linear regression and polynomial regression.

### Classification

Logistic regression and decision trees.

## Unsupervised Learning

Clustering and dimensionality reduction.
"""
    doc = Document.from_text(md_text, source="ml_guide.md", title="ML Guide")
    chunker = MarkdownHeaderChunker(max_chunk_size=500)
    chunks = chunker.chunk(doc)

    assert len(chunks) == 5

    # Check regression chunk metadata
    regression_chunk = next(c for c in chunks if "Linear regression" in c.content)
    assert regression_chunk.metadata["H1"] == "Machine Learning"
    assert regression_chunk.metadata["H2"] == "Supervised Learning"
    assert regression_chunk.metadata["H3"] == "Regression"
    assert regression_chunk.metadata["header_path"] == "Machine Learning > Supervised Learning > Regression"
    assert regression_chunk.metadata["current_header"] == "Regression"
    assert regression_chunk.metadata["header_level"] == "3"
    assert regression_chunk.metadata["source"] == "ml_guide.md"
    assert regression_chunk.start_char_index is not None
    assert regression_chunk.end_char_index is not None


def test_markdown_header_chunker_without_headers() -> None:
    plain_text = "Just a plain markdown document without any hashtag headers."
    doc = Document.from_text(plain_text, source="plain.md")
    chunker = MarkdownHeaderChunker()
    chunks = chunker.chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].content == plain_text
    assert chunks[0].start_char_index == 0
    assert chunks[0].end_char_index == len(plain_text)
