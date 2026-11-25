"""Manifest specification for Xeren Plugin #8: Experience/Feedback Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

EXPERIENCE_PLUGIN_MANIFEST = PluginManifest(
    name="experience",
    version="0.1.0",
    description="Structured experience and feedback memory layer enabling task history tracking, failure avoidance, user feedback incorporation, pattern detection, and lesson extraction without modifying model weights.",
    capabilities=[
        PluginCapability.EXPERIENCE_RECORD.value,
        PluginCapability.EXPERIENCE_RETRIEVAL.value,
        PluginCapability.SUCCESS_HISTORY.value,
        PluginCapability.FAILURE_HISTORY.value,
        PluginCapability.USER_FEEDBACK.value,
        PluginCapability.PATTERN_DETECTION.value,
        PluginCapability.LESSON_EXTRACTION.value,
        PluginCapability.EXPERIENCE_RANKING.value,
        PluginCapability.FAILURE_AVOIDANCE.value,
        PluginCapability.OUTCOME_TRACKING.value,
    ],
    input_schema_name="ExperienceInput",
    output_schema_name="ExperienceResult",
    author="Xeren Core Team",
    metadata={
        "category": "experience_and_feedback",
        "in_memory_default": True,
        "mongo_supported": True,
        "secret_sanitization": True,
        "deduplication": True,
        "self_training": False,
    },
)

__all__ = ["EXPERIENCE_PLUGIN_MANIFEST"]
