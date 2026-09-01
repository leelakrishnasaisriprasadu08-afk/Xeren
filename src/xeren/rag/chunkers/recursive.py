"""Hierarchical and character-based document chunkers with provenance tracking."""

from typing import List, Optional, Union

from xeren.rag.chunkers.base import BaseChunker
from xeren.rag.chunkers.config import ChunkingConfig
from xeren.rag.document import Document, DocumentChunk


class CharacterChunker(BaseChunker):
    """Fixed-size character chunker with sliding window overlap and offset tracking."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        config: Optional[ChunkingConfig] = None,
    ) -> None:
        if config:
            self.chunk_size = config.chunk_size
            self.chunk_overlap = config.chunk_overlap
        else:
            if chunk_size <= 0:
                raise ValueError("chunk_size must be positive")
            if chunk_overlap < 0 or chunk_overlap >= chunk_size:
                raise ValueError("chunk_overlap must be non-negative and less than chunk_size")
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> List[DocumentChunk]:
        text = document.content
        if not text:
            return []

        chunks_data: List[tuple[str, int, int]] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            chunks_data.append((chunk_text, start, end))
            if end == len(text):
                break
            start += step

        total = len(chunks_data)
        result: List[DocumentChunk] = []
        for idx, (piece, s_idx, e_idx) in enumerate(chunks_data):
            chunk_meta = dict(document.metadata.extra)
            chunk_meta.update({
                "source": document.metadata.source,
                "title": document.metadata.title,
                "chunk_index": idx,
                "total_chunks": total,
                "start_char_index": s_idx,
                "end_char_index": e_idx,
            })
            result.append(
                DocumentChunk(
                    document_id=document.id,
                    content=piece,
                    chunk_index=idx,
                    total_chunks=total,
                    start_char_index=s_idx,
                    end_char_index=e_idx,
                    metadata=chunk_meta,
                )
            )
        return result


class RecursiveTextChunker(BaseChunker):
    """Hierarchical text chunker preserving paragraphs, sentences, and words."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        separators: Optional[List[str]] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> None:
        if config:
            self.config = config
        else:
            self.config = ChunkingConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators if separators is not None else ["\n\n", "\n", " ", ""],
            )

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: List[str] = []
        for s in splits:
            if not s:
                continue
            if len(s) < self.config.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s[: self.config.chunk_size])
                else:
                    sub_chunks = self._split_text(s, new_separators)
                    final_chunks.extend(sub_chunks)

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs: List[str] = []
        current_doc: List[str] = []
        total_len = 0

        for split in splits:
            split_len = len(split)
            sep_len = len(separator) if current_doc else 0

            if total_len + split_len + sep_len > self.config.chunk_size:
                if current_doc:
                    doc_str = separator.join(current_doc)
                    if self.config.strip_whitespace:
                        doc_str = doc_str.strip()
                    if doc_str:
                        docs.append(doc_str)
                    while total_len > self.config.chunk_overlap and current_doc:
                        removed = current_doc.pop(0)
                        total_len -= len(removed) + (len(separator) if current_doc else 0)
                current_doc.append(split)
                total_len = sum(len(x) for x in current_doc) + (len(separator) * (len(current_doc) - 1))
            else:
                current_doc.append(split)
                total_len += split_len + sep_len

        if current_doc:
            doc_str = separator.join(current_doc)
            if self.config.strip_whitespace:
                doc_str = doc_str.strip()
            if doc_str:
                docs.append(doc_str)

        return docs

    def chunk(self, document: Document) -> List[DocumentChunk]:
        text = document.content
        if not text:
            return []

        raw_pieces = self._split_text(text, self.config.separators)
        if not raw_pieces:
            return []

        total = len(raw_pieces)
        chunks: List[DocumentChunk] = []
        cursor = 0

        for idx, piece in enumerate(raw_pieces):
            # Calculate character offset in parent document
            start_pos = text.find(piece, cursor)
            if start_pos == -1:
                start_pos = text.find(piece)
            end_pos = start_pos + len(piece) if start_pos != -1 else None
            if start_pos != -1:
                cursor = start_pos + 1

            chunk_meta = dict(document.metadata.extra)
            chunk_meta.update({
                "source": document.metadata.source,
                "title": document.metadata.title,
                "chunk_index": idx,
                "total_chunks": total,
                "start_char_index": start_pos if start_pos != -1 else None,
                "end_char_index": end_pos,
            })
            chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    content=piece,
                    chunk_index=idx,
                    total_chunks=total,
                    start_char_index=start_pos if start_pos != -1 else None,
                    end_char_index=end_pos,
                    metadata=chunk_meta,
                )
            )

        return chunks
