"""Registry managing internal research tools and providers."""

from typing import Dict, Optional

from xeren.models.base import BaseLLM
from xeren.plugins.research.tools.base import BaseResearchTool
from xeren.plugins.research.tools.evidence import EvidenceExtractionTool
from xeren.plugins.research.tools.ranking import SourceRankingTool
from xeren.plugins.research.tools.search import BaseSearchEngine, MockSearchEngine
from xeren.plugins.research.tools.synthesis import SynthesisTool


class ResearchToolRegistry:
    """Registry coordinating all internal tools utilized by the research workflow."""

    def __init__(
        self,
        search_engine: Optional[BaseSearchEngine] = None,
        ranking_tool: Optional[SourceRankingTool] = None,
        evidence_tool: Optional[EvidenceExtractionTool] = None,
        synthesis_tool: Optional[SynthesisTool] = None,
        llm: Optional[BaseLLM] = None,
    ) -> None:
        self.search_engine = search_engine or MockSearchEngine()
        self.ranking_tool = ranking_tool or SourceRankingTool()
        self.evidence_tool = evidence_tool or EvidenceExtractionTool(llm=llm)
        self.synthesis_tool = synthesis_tool or SynthesisTool(llm=llm)
        self._tools: Dict[str, BaseResearchTool] = {}

        self.register(self.ranking_tool)
        self.register(self.evidence_tool)
        self.register(self.synthesis_tool)

    def register(self, tool: BaseResearchTool) -> None:
        """Register an internal research tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseResearchTool]:
        """Retrieve a registered internal tool by name."""
        return self._tools.get(name)

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject or update the active LLM provider across relevant tools."""
        self.evidence_tool.llm = llm
        self.synthesis_tool.llm = llm

    def set_search_engine(self, engine: BaseSearchEngine) -> None:
        """Update the active search engine provider."""
        self.search_engine = engine


__all__ = ["ResearchToolRegistry"]
