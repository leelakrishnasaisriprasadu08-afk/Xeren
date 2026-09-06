"""Tool registry coordinating experience store, sanitizer, recorder, retriever, feedback, ranking, and pattern tools."""

from typing import Optional

from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.tools.feedback import ExperienceFeedbackTool
from xeren.plugins.experience.tools.patterns import ExperiencePatternTool
from xeren.plugins.experience.tools.ranking import ExperienceRankingTool
from xeren.plugins.experience.tools.recorder import ExperienceRecorderTool
from xeren.plugins.experience.tools.retriever import ExperienceRetrieverTool
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


class ExperienceToolRegistry:
    """Configures and binds modular experience tools to the active persistence store."""

    def __init__(
        self,
        store: Optional[BaseExperienceStore] = None,
        sanitizer: Optional[ExperienceSanitizerTool] = None,
        recorder_tool: Optional[ExperienceRecorderTool] = None,
        retriever_tool: Optional[ExperienceRetrieverTool] = None,
        feedback_tool: Optional[ExperienceFeedbackTool] = None,
        ranking_tool: Optional[ExperienceRankingTool] = None,
        pattern_tool: Optional[ExperiencePatternTool] = None,
    ) -> None:
        self.store = store or InMemoryExperienceStore()
        self.sanitizer = sanitizer or ExperienceSanitizerTool()
        self.recorder_tool = recorder_tool or ExperienceRecorderTool(
            store=self.store, sanitizer=self.sanitizer
        )
        self.retriever_tool = retriever_tool or ExperienceRetrieverTool(store=self.store)
        self.feedback_tool = feedback_tool or ExperienceFeedbackTool(
            store=self.store, sanitizer=self.sanitizer
        )
        self.ranking_tool = ranking_tool or ExperienceRankingTool()
        self.pattern_tool = pattern_tool or ExperiencePatternTool()

    def set_store(self, store: BaseExperienceStore) -> None:
        """Swap or rebind active persistence backend."""
        self.store = store
        self.recorder_tool.store = store
        self.retriever_tool.store = store
        self.feedback_tool.store = store


__all__ = ["ExperienceToolRegistry"]
