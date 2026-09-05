"""Tests for KnowledgePlugin multi-strategy retrieval, filtering, and thresholding."""

import pytest

from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.knowledge.schemas import KnowledgeInput, RetrievalMode
from xeren.plugins.knowledge.tools.retrieval import KnowledgeRetrievalTool
from xeren.rag.document import Document
from xeren.rag.retrieval.filter import FilterCondition, FilterOperator, MetadataFilter


@pytest.fixture
def populated_plugin() -> KnowledgePlugin:
    """Fixture providing a KnowledgePlugin pre-populated with diverse test documents."""
    plugin = KnowledgePlugin()
    docs = [
        Document.from_text(
            text="Transformer models utilize self-attention mechanisms to process tokens in parallel.",
            source="nlp_paper.pdf",
            doc_id="doc-transformers",
            extra={"domain": "nlp", "level": "advanced", "year": 2017},
        ),
        Document.from_text(
            text="Convolutional neural networks apply kernel filters over spatial grids for computer vision.",
            source="vision_paper.pdf",
            doc_id="doc-convolution",
            extra={"domain": "vision", "level": "intermediate", "year": 2015},
        ),
        Document.from_text(
            text="Reinforcement learning agents optimize policy value functions to maximize cumulative rewards.",
            source="rl_paper.pdf",
            doc_id="doc-rl",
            extra={"domain": "rl", "level": "advanced", "year": 2020},
        ),
        Document.from_text(
            text="Vector databases store dense embeddings and perform fast approximate nearest neighbor search.",
            source="vectordb_guide.md",
            doc_id="doc-vector-db",
            extra={"domain": "infrastructure", "level": "intermediate", "year": 2023},
        ),
    ]
    plugin.ingest(documents=docs)
    return plugin


def test_dense_retrieval_mode(populated_plugin: KnowledgePlugin):
    """Verify dense retrieval mode utilizes vector embeddings."""
    res = populated_plugin.query(
        query="self-attention parallel tokens",
        retrieval_mode=RetrievalMode.DENSE,
        top_k=2,
    )
    assert res.operation.value == "query"
    assert len(res.retrieved_chunks) > 0
    assert len(res.retrieved_chunks) <= 2


def test_keyword_retrieval_mode(populated_plugin: KnowledgePlugin):
    """Verify keyword retrieval mode utilizes BM25 sparse search."""
    res = populated_plugin.query(
        query="convolutional spatial grids",
        retrieval_mode=RetrievalMode.KEYWORD,
        top_k=2,
    )
    assert len(res.retrieved_chunks) > 0
    assert "Convolutional" in res.retrieved_chunks[0].content


def test_hybrid_retrieval_mode(populated_plugin: KnowledgePlugin):
    """Verify hybrid retrieval mode combines dense and sparse rankings."""
    res = populated_plugin.query(
        query="reinforcement policy rewards",
        retrieval_mode=RetrievalMode.HYBRID,
        top_k=3,
    )
    assert len(res.retrieved_chunks) > 0
    assert any("Reinforcement" in c.content for c in res.retrieved_chunks)
    assert len(res.retrieval_scores) > 0


def test_metadata_filtering(populated_plugin: KnowledgePlugin):
    """Verify metadata filter constrains retrieval to matching chunks."""
    filt = MetadataFilter(
        conditions=[
            FilterCondition(field="domain", operator=FilterOperator.EQ, value="vision")
        ]
    )
    res = populated_plugin.query(
        query="neural network",
        retrieval_mode=RetrievalMode.HYBRID,
        filter=filt,
        top_k=4,
    )
    assert len(res.retrieved_chunks) > 0
    for chunk in res.retrieved_chunks:
        assert chunk.metadata.get("domain") == "vision"


def test_top_k_limiting(populated_plugin: KnowledgePlugin):
    """Verify top_k bounds candidate selection."""
    res = populated_plugin.query(
        query="models",
        top_k=2,
        top_n=2,
    )
    assert len(res.retrieved_chunks) <= 2


def test_min_score_filtering(populated_plugin: KnowledgePlugin):
    """Verify min_score filters out candidates with scores below threshold."""
    # When min_score is high, low scoring candidates are excluded
    res = populated_plugin.query(
        query="completely unrelated query about baking sourdough bread and pastry",
        min_score=0.99,
    )
    assert len(res.retrieved_chunks) == 0


def test_empty_knowledge_base_retrieval():
    """Verify querying an empty knowledge base handles gracefully and reports gaps."""
    plugin = KnowledgePlugin()
    res = populated = plugin.query(query="Where is the data?")
    assert len(res.retrieved_chunks) == 0
    assert len(res.ranked_results) == 0
    assert len(res.knowledge_gaps) >= 1
    assert "No relevant knowledge chunks found" in res.knowledge_gaps[0]


def test_retrieval_tool_direct(populated_plugin: KnowledgePlugin):
    """Verify KnowledgeRetrievalTool direct operation."""
    tool = KnowledgeRetrievalTool(
        dense_retriever=populated_plugin.workflow.dense_retriever,
        keyword_retriever=populated_plugin.workflow.keyword_retriever,
        hybrid_retriever=populated_plugin.workflow.hybrid_retriever,
    )

    candidates = tool.retrieve("vector databases", mode=RetrievalMode.KEYWORD, top_k=2)
    assert len(candidates) > 0
