"""Unit tests for text and document normalizers."""

from xeren.rag.document import Document
from xeren.rag.normalizers.text_normalizer import CompositeNormalizer, TextNormalizer


def test_text_normalizer_line_endings_and_whitespace() -> None:
    raw = "Line 1   \r\n\r\n\r\n\r\nLine 2   \r\n"
    doc = Document.from_text(raw, source="test")

    normalizer = TextNormalizer(collapse_blank_lines=True, max_consecutive_blank_lines=2)
    normalized = normalizer.normalize(doc)

    assert "\r" not in normalized.content
    assert normalized.content == "Line 1\n\nLine 2"


def test_text_normalizer_unicode_and_controls() -> None:
    # Full-width characters and control chars (null byte)
    raw = "Ｈｅｌｌｏ\x00 World"
    doc = Document.from_text(raw, source="test")

    normalizer = TextNormalizer(normalize_unicode=True, remove_control_chars=True)
    normalized = normalizer.normalize(doc)

    assert normalized.content == "Hello World"


def test_composite_normalizer() -> None:
    doc = Document.from_text("  Raw   \r\nText  ", source="test")
    norm1 = TextNormalizer()
    composite = CompositeNormalizer([norm1])
    res = composite.normalize(doc)
    assert res.content == "Raw\nText"
