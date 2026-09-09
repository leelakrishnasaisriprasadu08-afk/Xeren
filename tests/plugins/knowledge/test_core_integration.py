"""Tests for end-to-end Core -> PluginManager -> KnowledgePlugin integration."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.knowledge.schemas import KnowledgeResult, RetrievalMode
from xeren.rag.document import Document


def test_core_auto_registers_knowledge_plugin():
    """Verify XerenCore automatically registers KnowledgePlugin by default."""
    core = XerenCore(auto_register_defaults=True)
    assert core.has_plugin("knowledge")
    assert core.has_plugin("research")

    plugin = core.get_plugin("knowledge")
    assert plugin is not None
    assert plugin.name == "knowledge"


def test_core_execute_plugin_generic():
    """Verify core.execute_plugin works for knowledge operations."""
    core = XerenCore()
    # Ingest some knowledge first
    core.ingest_knowledge(texts=["Hyperparameter optimization using Bayesian methods."])

    exec_res = core.execute_plugin(
        name="knowledge",
        input_data={"query": "Bayesian optimization", "top_k": 3},
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, KnowledgeResult)
    assert len(exec_res.output.retrieved_chunks) >= 1


@pytest.mark.asyncio
async def test_core_aexecute_plugin_generic():
    """Verify core.aexecute_plugin works asynchronously."""
    core = XerenCore()
    await core.aingest_knowledge(texts=["Distributed model training with ZeRO stages."])

    exec_res = await core.aexecute_plugin(
        name="knowledge",
        input_data={"query": "Distributed training ZeRO", "top_k": 2},
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, KnowledgeResult)


def test_core_knowledge_convenience_method():
    """Verify core.knowledge high-level method."""
    core = XerenCore()
    core.ingest_knowledge(
        texts=["Linear attention models achieve sub-quadratic complexity in sequence length."],
        source="attention_paper",
    )

    res = core.knowledge(query="linear attention sequence length", retrieval_mode=RetrievalMode.HYBRID)
    assert isinstance(res, KnowledgeResult)
    assert len(res.retrieved_chunks) >= 1
    assert res.context is not None
    assert len(res.provenance) >= 1
    assert res.provenance[0].source == "attention_paper"


@pytest.mark.asyncio
async def test_core_aknowledge_convenience_method():
    """Verify core.aknowledge async high-level method."""
    core = XerenCore()
    await core.aingest_knowledge(
        texts=["Mixture of Experts activates a subset of neural network parameters per token."],
    )

    res = await core.aknowledge(query="Mixture of Experts tokens")
    assert isinstance(res, KnowledgeResult)
    assert len(res.retrieved_chunks) >= 1


def test_core_multi_plugin_coexistence():
    """Verify ResearchPlugin and KnowledgePlugin co-exist and execute independently in XerenCore."""
    core = XerenCore()

    # 1. Execute Research Plugin
    research_res = core.research("Generative AI agents")
    assert research_res.objective == "Generative AI agents"
    assert len(research_res.sources) > 0

    # 2. Ingest into Knowledge Plugin
    core.ingest_knowledge(texts=["Agent memory systems utilize working memory and episodic stores."])

    # 3. Execute Knowledge Plugin
    knowledge_res = core.knowledge("episodic stores agent memory")
    assert len(knowledge_res.retrieved_chunks) >= 1

    # Both succeeded and both plugins remain registered and operational
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")


def test_core_health_check_includes_knowledge():
    """Verify Core health check surveys KnowledgePlugin."""
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert "knowledge" in health["plugins"]
    assert health["plugins"]["knowledge"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_core_acheck_health():
    """Verify async Core health check."""
    core = XerenCore()
    health = await core.acheck_health()
    assert health["healthy"] is True
    assert "knowledge" in health["plugins"]
