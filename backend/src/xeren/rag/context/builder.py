"""Context builder for selecting, ranking, and assembling grounded prompt context."""

import re
from typing import List, Optional

from xeren.rag.context.types import Citation, ContextConfig, GroundedContext
from xeren.rag.retrieval.types import SearchResult


class ContextBuilder:
    """Selects high-relevance chunks and constructs grounded context blocks with provenance citations."""

    BEGIN_DELIMITER = "--- BEGIN GROUNDED CONTEXT ---"
    END_DELIMITER = "--- END GROUNDED CONTEXT ---"

    # Known prompt injection control tokens to neutralize
    INJECTION_PATTERNS = [
        (re.compile(r"<\|im_start\|>", re.IGNORECASE), "[control_tag: im_start]"),
        (re.compile(r"<\|im_end\|>", re.IGNORECASE), "[control_tag: im_end]"),
        (re.compile(r"\[INST\]", re.IGNORECASE), "[control_tag: INST]"),
        (re.compile(r"\[/INST\]", re.IGNORECASE), "[control_tag: /INST]"),
        (re.compile(r"<<SYS>>", re.IGNORECASE), "[control_tag: SYS]"),
        (re.compile(r"<</SYS>>", re.IGNORECASE), "[control_tag: /SYS]"),
    ]

    def __init__(self, config: Optional[ContextConfig] = None) -> None:
        self.config = config or ContextConfig()

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _sanitize_chunk_content(self, text: str) -> str:
        """Escape context boundary delimiters and prompt injection control tokens."""
        # 1. Neutralize delimiter breakout attacks
        sanitized = text.replace(self.BEGIN_DELIMITER, "[escaped_delimiter: BEGIN GROUNDED CONTEXT]")
        sanitized = sanitized.replace(self.END_DELIMITER, "[escaped_delimiter: END GROUNDED CONTEXT]")

        # 2. Neutralize chat template injection tokens
        for pattern, replacement in self.INJECTION_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized.strip()

    def _format_chunk_block(self, result: SearchResult, citation_id: int) -> str:
        meta = result.chunk.metadata
        source = meta.get("source", "unknown")
        title = meta.get("title")
        header_path = meta.get("header_path")

        header_info = f" | Section: {header_path}" if (self.config.include_header_metadata and header_path) else ""
        title_info = f" ({title})" if title and title != source else ""

        citation_header = f"[{citation_id}] Source: {source}{title_info}{header_info}"
        sanitized_content = self._sanitize_chunk_content(result.chunk.content)
        return f"{citation_header}\n{sanitized_content}"

    def build(self, results: List[SearchResult]) -> GroundedContext:
        """Select top chunks within token and count budgets, constructing grounded context."""
        if not results:
            return GroundedContext(
                formatted_text="",
                selected_chunks=[],
                citations=[],
                total_characters=0,
                estimated_tokens=0,
                has_context=False,
            )

        selected_chunks: List[SearchResult] = []
        citations: List[Citation] = []
        formatted_blocks: List[str] = []
        current_tokens = 0

        # Filter by minimum score threshold
        eligible_results = [
            r for r in results if r.score >= self.config.min_score_threshold
        ]

        for result in eligible_results:
            if len(selected_chunks) >= self.config.max_chunks:
                break

            citation_id = len(selected_chunks) + 1
            block_text = self._format_chunk_block(result, citation_id)
            block_tokens = self._estimate_tokens(block_text)

            # Check token budget
            if current_tokens + block_tokens > self.config.max_tokens and selected_chunks:
                # Token budget reached, skip remaining chunks
                break

            selected_chunks.append(result)
            formatted_blocks.append(block_text)
            current_tokens += block_tokens

            # Create citation reference
            meta = result.chunk.metadata
            citations.append(
                Citation(
                    citation_id=citation_id,
                    source=str(meta.get("source", "unknown")),
                    title=meta.get("title"),
                    header_path=meta.get("header_path"),
                    chunk_id=result.chunk.chunk_id,
                    start_char_index=result.chunk.start_char_index,
                    end_char_index=result.chunk.end_char_index,
                    metadata=meta,
                )
            )

        if not selected_chunks:
            return GroundedContext(
                formatted_text="",
                selected_chunks=[],
                citations=[],
                total_characters=0,
                estimated_tokens=0,
                has_context=False,
            )

        joined_blocks = "\n\n".join(formatted_blocks)
        formatted_text = (
            f"{self.BEGIN_DELIMITER}\n"
            f"{joined_blocks}\n"
            f"{self.END_DELIMITER}"
        )

        return GroundedContext(
            formatted_text=formatted_text,
            selected_chunks=selected_chunks,
            citations=citations,
            total_characters=len(formatted_text),
            estimated_tokens=self._estimate_tokens(formatted_text),
            has_context=True,
        )
