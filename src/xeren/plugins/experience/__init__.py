"""Xeren Plugin #8: Experience/Feedback Plugin.

Structured experience and outcome evaluation memory layer enabling task learning, failure
avoidance, user feedback capture, and pattern extraction without modifying model weights.
"""

from xeren.plugins.experience.manifest import EXPERIENCE_PLUGIN_MANIFEST
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.registry import ExperienceToolRegistry
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    ExperienceStats,
    FailureWarning,
    LessonItem,
    OutcomeType,
    UserFeedback,
)
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.stores.mongo import MongoExperienceStore
from xeren.plugins.experience.tools.feedback import ExperienceFeedbackTool
from xeren.plugins.experience.tools.patterns import ExperiencePatternTool
from xeren.plugins.experience.tools.ranking import ExperienceRankingTool
from xeren.plugins.experience.tools.recorder import ExperienceRecorderTool
from xeren.plugins.experience.tools.retriever import ExperienceRetrieverTool
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool
from xeren.plugins.experience.workflow import ExperienceWorkflow

__all__ = [
    "ExperiencePlugin",
    "EXPERIENCE_PLUGIN_MANIFEST",
    "ExperienceToolRegistry",
    "ExperienceWorkflow",
    "ExperienceItem",
    "ExperienceInput",
    "ExperienceResult",
    "ExperienceOperation",
    "OutcomeType",
    "UserFeedback",
    "FailureWarning",
    "LessonItem",
    "ExperienceStats",
    "BaseExperienceStore",
    "InMemoryExperienceStore",
    "MongoExperienceStore",
    "ExperienceSanitizerTool",
    "ExperienceRecorderTool",
    "ExperienceRetrieverTool",
    "ExperienceFeedbackTool",
    "ExperienceRankingTool",
    "ExperiencePatternTool",
]
