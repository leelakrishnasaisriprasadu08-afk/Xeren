"""Context construction tool wrapping existing Xeren ContextBuilder."""

import logging
from typing import List

from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import GroundedContext
from xeren.rag.retrieval.types import SearchResult

logger = logging.getLogger("xeren.plugins.knowledge.tools.context")


class KnowledgeContextTool:
    """Delegates context formatting directly to existing Xeren ContextBuilder."""

    def __init__(self, builder: ContextBuilder) -> None:
        self.builder = builder

    def build_context(self, results: List[SearchResult]) -> GroundedContext:
        """Build grounded, delimited context block with citation markers from retrieved results."""
        return self.builder.build(results)


__all__ = ["KnowledgeContextTool"]
