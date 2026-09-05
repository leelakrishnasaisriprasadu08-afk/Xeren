"""Tests for Core -> PluginManager -> WebsitePlugin end-to-end integration."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.coding.schemas import CodingOperation
from xeren.plugins.website.schemas import (
    WebsiteOperation,
    WebsiteResult,
    WebsiteType,
)


def test_core_auto_registers_website_plugin():
    """Verify XerenCore auto-registers WebsitePlugin alongside Research, Knowledge, and Coding."""
    core = XerenCore(auto_register_defaults=True)
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")
    assert core.has_plugin("website")

    plugin = core.get_plugin("website")
    assert plugin is not None
    assert plugin.name == "website"


def test_core_execute_plugin_website():
    """Verify core.execute_plugin for website operations."""
    core = XerenCore()
    exec_res = core.execute_plugin(
        name="website",
        input_data={
            "requirement": "Build a SaaS landing page",
            "operation": "generate",
            "website_type": "landing_page",
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, WebsiteResult)
    assert exec_res.output.operation == WebsiteOperation.GENERATE
    assert len(exec_res.output.files) >= 3


@pytest.mark.asyncio
async def test_core_aexecute_plugin_website():
    """Verify async core.aexecute_plugin for website operations."""
    core = XerenCore()
    exec_res = await core.aexecute_plugin(
        name="website",
        input_data={
            "requirement": "Build an educational website",
            "operation": "generate",
            "website_type": "educational",
        },
    )
    assert exec_res.success is True
    assert isinstance(exec_res.output, WebsiteResult)


def test_core_website_convenience_method():
    """Verify high-level core.website convenience method."""
    core = XerenCore()
    result = core.website(
        requirement="Create a mobile app showcase site",
        operation=WebsiteOperation.GENERATE,
        website_type=WebsiteType.LANDING_PAGE,
    )
    assert isinstance(result, WebsiteResult)
    assert result.operation == WebsiteOperation.GENERATE
    assert result.success is True
    assert len(result.files) >= 3


@pytest.mark.asyncio
async def test_core_awebsite_convenience_method():
    """Verify async high-level core.awebsite convenience method."""
    core = XerenCore()
    result = await core.awebsite(
        requirement="Create an online resume",
        operation=WebsiteOperation.GENERATE,
        website_type=WebsiteType.PORTFOLIO,
    )
    assert isinstance(result, WebsiteResult)
    assert result.operation == WebsiteOperation.GENERATE
    assert result.success is True


def test_core_all_four_plugins_coexistence():
    """Verify Research, Knowledge, Coding, and Website plugins all coexist and function in one Core instance."""
    core = XerenCore()

    # 1. Research Plugin
    res_research = core.research("Transformer neural architectures")
    assert res_research.objective == "Transformer neural architectures"

    # 2. Knowledge Plugin
    core.ingest_knowledge(texts=["Attention Is All You Need introduced the Transformer."])
    res_knowledge = core.knowledge("Transformer paper")
    assert len(res_knowledge.retrieved_chunks) >= 1

    # 3. Coding Plugin
    res_coding = core.coding(
        operation=CodingOperation.SYNTAX_CHECK,
        source_code="def evaluate(x): return x * 2",
    )
    assert res_coding.syntax_valid is True

    # 4. Website Plugin
    res_website = core.website(
        requirement="Build a landing page for Transformer research",
        operation=WebsiteOperation.GENERATE,
    )
    assert res_website.success is True
    assert len(res_website.files) >= 3

    # Confirm all 4 plugins remain registered and healthy
    assert core.has_plugin("research")
    assert core.has_plugin("knowledge")
    assert core.has_plugin("coding")
    assert core.has_plugin("website")


def test_core_health_check_includes_website():
    """Verify Core health check includes WebsitePlugin and reports healthy."""
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert "website" in health["plugins"]
    assert health["plugins"]["website"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_core_acheck_health_includes_website():
    """Verify async Core health check includes WebsitePlugin."""
    core = XerenCore()
    health = await core.acheck_health()
    assert health["healthy"] is True
    assert "website" in health["plugins"]
    assert health["plugins"]["website"]["status"] == "healthy"
