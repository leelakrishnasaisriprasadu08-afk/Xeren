"""Markdown header chunker preserving hierarchical document structure and provenance."""

import re
from typing import Dict, List, Optional, Tuple

from xeren.rag.chunkers.base import BaseChunker
from xeren.rag.chunkers.recursive import RecursiveTextChunker
from xeren.rag.document import Document, DocumentChunk


class MarkdownHeaderChunker(BaseChunker):
    """Chunks Markdown text along header boundaries while attaching hierarchical breadcrumbs."""

    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        max_chunk_size: int = 1500,
        sub_chunker: Optional[BaseChunker] = None,
    ) -> None:
        self.max_chunk_size = max_chunk_size
        self.sub_chunker = sub_chunker or RecursiveTextChunker(chunk_size=max_chunk_size)

    def _extract_sections(self, text: str) -> List[Tuple[Dict[str, str], str, int, int]]:
        """Split text into sections with active header hierarchy stack and character ranges."""
        sections: List[Tuple[Dict[str, str], str, int, int]] = []
        matches = list(self.HEADER_PATTERN.finditer(text))

        if not matches:
            return [({}, text, 0, len(text))]

        # Text before first header
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()]
            if preamble.strip():
                sections.append(({}, preamble, 0, matches[0].start()))

        header_stack: List[Tuple[int, str]] = []  # [(level, title)]

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_content = text[start_pos:end_pos]

            # Update header hierarchy stack
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, title))

            header_meta = {
                f"H{lvl}": t for lvl, t in header_stack
            }
            header_meta["header_path"] = " > ".join(t for _, t in header_stack)
            header_meta["current_header"] = title
            header_meta["header_level"] = str(level)

            sections.append((header_meta, section_content, start_pos, end_pos))

        return sections

    def chunk(self, document: Document) -> List[DocumentChunk]:
        text = document.content
        if not text:
            return []

        sections = self._extract_sections(text)
        intermediate_chunks: List[Tuple[str, Dict[str, str], int, int]] = []

        for header_meta, sec_text, s_idx, e_idx in sections:
            if len(sec_text) <= self.max_chunk_size:
                intermediate_chunks.append((sec_text, header_meta, s_idx, e_idx))
            else:
                # Sub-chunk large section
                sub_doc = Document(
                    id=document.id,
                    content=sec_text,
                    metadata=document.metadata,
                )
                sub_chunks = self.sub_chunker.chunk(sub_doc)
                for sc in sub_chunks:
                    sub_start = s_idx + (sc.start_char_index or 0)
                    sub_end = s_idx + (sc.end_char_index or len(sc.content))
                    intermediate_chunks.append((sc.content, header_meta, sub_start, sub_end))

        total = len(intermediate_chunks)
        final_chunks: List[DocumentChunk] = []

        for idx, (chunk_text, h_meta, s_idx, e_idx) in enumerate(intermediate_chunks):
            meta = dict(document.metadata.extra)
            meta.update({
                "source": document.metadata.source,
                "title": document.metadata.title,
                "chunk_index": idx,
                "total_chunks": total,
                "start_char_index": s_idx,
                "end_char_index": e_idx,
            })
            meta.update(h_meta)

            final_chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk_text,
                    chunk_index=idx,
                    total_chunks=total,
                    start_char_index=s_idx,
                    end_char_index=e_idx,
                    metadata=meta,
                )
            )

        return final_chunks
