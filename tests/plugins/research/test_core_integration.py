"""Integration tests: Xeren Core → Plugin Manager → Research Plugin → Workflow → Result → Core."""

import pytest
from pydantic import BaseModel

from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.schemas import (
    RawSearchResult,
    ResearchDepth,
    ResearchInput,
    ResearchResult,
)
from xeren.plugins.research.tools.search import SearchAdapter


def test_core_initialization_with_research_plugin() -> None:
    core = XerenCore()
    assert core.has_plugin("research") is True
    manifests = core.list_plugins()
    assert any(m.name == "research" for m in manifests)


def test_core_execute_plugin_generic_interface() -> None:
    core = XerenCore()
    payload = {
        "query": "State of multi-agent LLM systems",
        "depth": "overview",
        "max_sources": 3,
    }
    exec_res = core.execute_plugin("research", payload)

    assert exec_res.success is True
    assert exec_res.plugin_name == "research"
    assert isinstance(exec_res.output, ResearchResult)
    assert exec_res.output.objective == "State of multi-agent LLM systems"
    assert len(exec_res.output.sources) > 0
    assert len(exec_res.output.evidence) > 0


def test_core_research_typed_convenience_interface() -> None:
    core = XerenCore()
    result = core.research(
        query="Self-supervised representation learning",
        depth=ResearchDepth.STANDARD,
        max_sources=4,
    )

    assert isinstance(result, ResearchResult)
    assert result.objective == "Self-supervised representation learning"
    assert len(result.findings) > 0
    assert len(result.evidence) > 0
    assert result.confidence_score >= 0.5


@pytest.mark.asyncio
async def test_core_aresearch_async_interface() -> None:
    core = XerenCore()
    result = await core.aresearch(
        query="Transformer attention complexity",
        depth=ResearchDepth.OVERVIEW,
        max_sources=2,
    )

    assert isinstance(result, ResearchResult)
    assert result.objective == "Transformer attention complexity"
    assert len(result.sources) > 0


def test_core_inject_custom_llm() -> None:
    """Verify that future trained Xeren Core LLM can be injected without altering the plugin."""
    trained_xeren_llm = MockLLM(
        canned_response="The trained Xeren Core model synthesized this verified response from retrieved evidence."
    )
    core = XerenCore(llm=trained_xeren_llm)

    result = core.research(
        query="LLM reasoning enhancements",
        depth=ResearchDepth.OVERVIEW,
    )

    assert "The trained Xeren Core model synthesized this verified response" in result.executive_summary


def test_core_replace_search_engine_via_adapter() -> None:
    """Verify that external search can be replaced with real provider adapter (e.g. Brave/Tavily)."""
    def simulated_real_search(query: str, max_results: int, domains: list[str] | None) -> list[RawSearchResult]:
        return [
            RawSearchResult(
                url="https://real-search-api.com/doc1",
                title="Verified External Search Document",
                snippet="Real live search results from external search provider adapter.",
                score=0.98,
            )
        ]

    custom_search_adapter = SearchAdapter(search_fn=simulated_real_search)
    custom_plugin = ResearchPlugin(search_engine=custom_search_adapter)

    core = XerenCore()
    core.register_plugin(custom_plugin, override=True)

    result = core.research("External Search Integration")
    assert result.sources[0].url == "https://real-search-api.com/doc1"
    assert "Real live search results" in result.evidence[0].fact_statement


def test_core_health_check() -> None:
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert health["core_llm"]["healthy"] is True
    assert "research" in health["plugins"]
    assert health["plugins"]["research"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_core_ahealth_check() -> None:
    core = XerenCore()
    health = await core.acheck_health()
    assert health["healthy"] is True
    assert health["core_llm"]["healthy"] is True
    assert health["plugins"]["research"]["status"] == "healthy"


def test_core_extensible_future_plugin_registration() -> None:
    """Demonstrate that future plugins (e.g. CodingPlugin) register without modifying Core architecture."""
    class FuturePluginInput(BaseModel):
        code: str

    class FuturePluginOutput(BaseModel):
        analysis: str

    class FutureAnalysisPlugin(BasePlugin):
        @property
        def manifest(self) -> PluginManifest:
            return PluginManifest(
                name="analysis",
                version="0.1.0",
                description="Future analysis plugin",
                capabilities=[PluginCapability.CODE_EXECUTION.value],
                input_schema_name="FuturePluginInput",
                output_schema_name="FuturePluginOutput",
            )

        @property
        def input_schema(self) -> type[BaseModel]:
            return FuturePluginInput

        @property
        def output_schema(self) -> type[BaseModel]:
            return FuturePluginOutput

        def execute(self, input_data, context=None) -> PluginExecutionResult:
            validated = self.validate_input(input_data)
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=FuturePluginOutput(analysis=f"Analyzed: {validated.code}"),  # type: ignore
            )

    core = XerenCore()
    core.register_plugin(FutureAnalysisPlugin())

    assert core.has_plugin("analysis") is True
    res = core.execute_plugin("analysis", {"code": "def foo(): pass"})
    assert res.success is True
    assert res.output.analysis == "Analyzed: def foo(): pass"  # type: ignore
