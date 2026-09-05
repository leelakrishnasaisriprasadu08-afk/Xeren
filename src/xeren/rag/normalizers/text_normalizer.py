"""Text normalization implementations for document cleaning."""

import re
from typing import List, Literal, Optional, cast
import unicodedata

from xeren.rag.document import Document
from xeren.rag.normalizers.base import BaseNormalizer

_NormalizationForm = Literal["NFC", "NFD", "NFKC", "NFKD"]


class TextNormalizer(BaseNormalizer):
    """Cleans Unicode anomalies, normalizes whitespace and line breaks."""

    def __init__(
        self,
        normalize_unicode: bool = True,
        unicode_form: str = "NFKC",
        strip_whitespace: bool = True,
        collapse_blank_lines: bool = True,
        max_consecutive_blank_lines: int = 2,
        remove_control_chars: bool = True,
    ) -> None:
        self.normalize_unicode = normalize_unicode
        self.unicode_form = unicode_form
        self.strip_whitespace = strip_whitespace
        self.collapse_blank_lines = collapse_blank_lines
        self.max_consecutive_blank_lines = max_consecutive_blank_lines
        self.remove_control_chars = remove_control_chars

    def _clean_text(self, text: str) -> str:
        # 1. Unicode normalization
        if self.normalize_unicode:
            form = cast(_NormalizationForm, self.unicode_form)
            text = unicodedata.normalize(form, text)

        # 2. Line ending normalization
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Control character filtering (preserve \n, \t)
        if self.remove_control_chars:
            text = "".join(ch for ch in text if ch in ("\n", "\t") or (unicodedata.category(ch)[0] != "C"))

        # 4. Trailing line whitespace stripping
        if self.strip_whitespace:
            lines = [line.rstrip() for line in text.split("\n")]
            text = "\n".join(lines)

        # 5. Collapse excessive blank lines
        if self.collapse_blank_lines:
            pattern = "\n{" + str(self.max_consecutive_blank_lines + 1) + ",}"
            replacement = "\n" * self.max_consecutive_blank_lines
            text = re.sub(pattern, replacement, text)

        return text.strip()

    def normalize(self, document: Document) -> Document:
        cleaned_content = self._clean_text(document.content)
        return Document(
            id=document.id,
            content=cleaned_content,
            metadata=document.metadata,
            doc_type=document.doc_type,
        )


class CompositeNormalizer(BaseNormalizer):
    """Chains multiple normalizers sequentially."""

    def __init__(self, normalizers: List[BaseNormalizer]) -> None:
        self.normalizers = normalizers

    def normalize(self, document: Document) -> Document:
        current_doc = document
        for normalizer in self.normalizers:
            current_doc = normalizer.normalize(current_doc)
        return current_doc
