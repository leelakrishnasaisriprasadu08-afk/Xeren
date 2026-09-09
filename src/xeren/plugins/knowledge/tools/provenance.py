"""Provenance mapping tool ensuring citation and source attribution preservation."""

import logging
from typing import List, Optional

from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.retrieval.types import SearchResult

logger = logging.getLogger("xeren.plugins.knowledge.tools.provenance")


class KnowledgeProvenanceTool:
    """Extracts and preserves source citations and chunk provenance from retrieved search results."""

    @staticmethod
    def extract_from_context(context: GroundedContext) -> List[Citation]:
        """Extract citations directly from an assembled GroundedContext."""
        return list(context.citations)

    @staticmethod
    def extract_from_results(results: List[SearchResult]) -> List[Citation]:
        """Extract Citation objects directly from a list of SearchResults when full context is not built."""
        citations: List[Citation] = []
        for idx, item in enumerate(results):
            meta = item.chunk.metadata
            citations.append(
                Citation(
                    citation_id=idx + 1,
                    source=str(meta.get("source", item.chunk.document_id)),
                    title=meta.get("title"),
                    header_path=meta.get("header_path"),
                    chunk_id=item.chunk.chunk_id,
                    start_char_index=item.chunk.start_char_index,
                    end_char_index=item.chunk.end_char_index,
                    metadata=meta,
                )
            )
        return citations

    @classmethod
    def get_provenance(
        cls,
        results: List[SearchResult],
        context: Optional[GroundedContext] = None,
    ) -> List[Citation]:
        """Get provenance citations, preferring context-generated citations if present."""
        if context is not None and context.citations:
            return cls.extract_from_context(context)
        return cls.extract_from_results(results)


__all__ = ["KnowledgeProvenanceTool"]
