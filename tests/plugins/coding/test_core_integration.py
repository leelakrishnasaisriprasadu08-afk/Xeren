"""Tests for end-to-end Core -> PluginManager -> CodingPlugin integration."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.coding.schemas import CodingOperation, CodingResult


def test_core_auto_registers_coding_plugin():
    """Verify XerenCore auto-registers CodingPlugin alongside Research and Knowledge."""
    core = XerenCore(auto_register_defaults=True)
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")

    plugin = core.get_plugin("coding")
    assert plugin is not None
    assert plugin.name == "coding"


def test_core_execute_plugin_coding():
    """Verify generic core.execute_plugin for coding operations."""
    core = XerenCore()
    exec_res = core.execute_plugin(
        name="coding",
        input_data={
            "operation": "syntax_check",
            "source_code": "def hello(): return 'world'",
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, CodingResult)
    assert exec_res.output.syntax_valid is True


@pytest.mark.asyncio
async def test_core_aexecute_plugin_coding():
    """Verify generic async core.aexecute_plugin for coding operations."""
    core = XerenCore()
    exec_res = await core.aexecute_plugin(
        name="coding",
        input_data={
            "operation": "syntax_check",
            "source_code": "val = 100",
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, CodingResult)


def test_core_coding_convenience_method():
    """Verify high-level core.coding convenience method."""
    core = XerenCore()
    result = core.coding(
        task="Write a function returning True",
        operation=CodingOperation.GENERATE,
    )
    assert isinstance(result, CodingResult)
    assert result.operation == CodingOperation.GENERATE
    assert len(result.files) == 1


@pytest.mark.asyncio
async def test_core_acoding_convenience_method():
    """Verify async high-level core.acoding convenience method."""
    core = XerenCore()
    result = await core.acoding(
        task="Write an async function",
        operation=CodingOperation.GENERATE,
    )
    assert isinstance(result, CodingResult)
    assert result.operation == CodingOperation.GENERATE


def test_core_all_three_plugins_coexistence():
    """Verify Research, Knowledge, and Coding plugins co-exist and execute in one Core instance."""
    core = XerenCore()

    # 1. Research Plugin
    res_research = core.research("Neural network architectures")
    assert res_research.objective == "Neural network architectures"

    # 2. Knowledge Plugin
    core.ingest_knowledge(texts=["Attention is all you need whitepaper introduces transformers."])
    res_knowledge = core.knowledge("attention whitepaper")
    assert len(res_knowledge.retrieved_chunks) >= 1

    # 3. Coding Plugin
    res_coding = core.coding(
        operation=CodingOperation.SYNTAX_CHECK,
        source_code="def attention(q, k, v): pass",
    )
    assert res_coding.syntax_valid is True

    # All three plugins remain registered and operational
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")


def test_core_health_check_includes_coding():
    """Verify Core health check surveys CodingPlugin."""
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert "coding" in health["plugins"]
    assert health["plugins"]["coding"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_core_acheck_health():
    """Verify async Core health check includes coding."""
    core = XerenCore()
    health = await core.acheck_health()
    assert health["healthy"] is True
    assert "coding" in health["plugins"]
