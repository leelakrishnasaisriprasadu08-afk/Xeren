"""Tests for KnowledgePlugin reranking, grounded context building, and provenance attribution."""

from typing import List, Optional

import pytest

from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.tools.context import KnowledgeContextTool
from xeren.plugins.knowledge.tools.provenance import KnowledgeProvenanceTool
from xeren.rag.document import Document
from xeren.rag.rerankers.base import BaseReranker
from xeren.rag.retrieval.types import SearchResult


class CustomInvertingReranker(BaseReranker):
    """Test reranker that reverses candidate order to test reranking delegation."""

    def rerank(self, query: str, results: List[SearchResult], top_n: Optional[int] = 5) -> List[SearchResult]:
        reversed_res = list(reversed(results))
        for idx, r in enumerate(reversed_res):
            r.score = 1.0 - (idx * 0.1)
        return reversed_res[:top_n]


@pytest.fixture
def populated_plugin() -> KnowledgePlugin:
    plugin = KnowledgePlugin()
    docs = [
        Document.from_text(
            text="Provenance attribution attaches exact source chunk IDs and character offsets to each cited snippet.",
            source="provenance_guide.md",
            doc_id="doc_rag_provenance",
            title="Provenance System",
        ),
        Document.from_text(
            text="Security delimiters and sanitization mitigate prompt injection risks in retrieved context blocks.",
            source="security_whitepaper.md",
            doc_id="doc_security_delimiters",
            title="Context Security",
        ),
    ]
    plugin.ingest(documents=docs)
    return plugin


def test_reranker_delegation(populated_plugin: KnowledgePlugin):
    """Verify custom reranker is invoked during retrieval workflow."""
    plugin = KnowledgePlugin(
        vector_store=populated_plugin.workflow.vector_store,
        embedding_model=populated_plugin.workflow.embedding_model,
        keyword_retriever=populated_plugin.workflow.keyword_retriever,
        reranker=CustomInvertingReranker(),
    )

    res = plugin.query(query="security provenance", top_k=2, top_n=2)
    assert len(res.ranked_results) == 2
    assert res.ranked_results[0].score >= res.ranked_results[1].score


def test_context_construction(populated_plugin: KnowledgePlugin):
    """Verify grounded context is constructed with delimiters and citations."""
    res = populated_plugin.query(query="Security delimiters prompt injection", include_context=True)
    assert res.context is not None
    assert res.context.formatted_text != ""
    assert "[1]" in res.context.formatted_text
    assert len(res.provenance) > 0


def test_provenance_preservation(populated_plugin: KnowledgePlugin):
    """Verify provenance citations map accurately to chunk IDs and sources."""
    res = populated_plugin.query(
        query="Provenance attribution exact source chunk IDs",
        include_context=True,
        include_provenance=True,
    )
    assert len(res.provenance) > 0
    citation = res.provenance[0]
    assert citation.citation_id == 1
    assert citation.chunk_id != ""
    assert citation.source in ["provenance_guide.md", "security_whitepaper.md"]


def test_provenance_without_context_formatting(populated_plugin: KnowledgePlugin):
    """Verify provenance citations are generated even when context formatting is disabled."""
    res = populated_plugin.query(
        query="sanitization prompt injection",
        include_context=False,
        include_provenance=True,
    )
    assert res.context is None
    assert len(res.provenance) > 0
    assert res.provenance[0].chunk_id != ""


def test_context_and_provenance_tools_direct(populated_plugin: KnowledgePlugin):
    """Verify KnowledgeContextTool and KnowledgeProvenanceTool direct operations."""
    candidates = populated_plugin.workflow.retrieval_tool.retrieve("security", top_k=2)
    context_tool = KnowledgeContextTool(populated_plugin.workflow.context_builder)
    grounded = context_tool.build_context(candidates)

    assert grounded is not None
    assert grounded.estimated_tokens > 0

    provenance_tool = KnowledgeProvenanceTool()
    cits_from_context = provenance_tool.extract_from_context(grounded)
    assert len(cits_from_context) == len(grounded.citations)

    cits_from_results = provenance_tool.extract_from_results(candidates)
    assert len(cits_from_results) == len(candidates)

