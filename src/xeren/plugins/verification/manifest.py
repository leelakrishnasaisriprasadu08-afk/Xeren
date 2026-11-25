"""Manifest specification for Xeren Plugin #7: Verification Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

VERIFICATION_PLUGIN_MANIFEST = PluginManifest(
    name="verification",
    version="0.1.0",
    description="Independent quality-control and outcome evaluation layer across modalities (text, code, data, facts, and structure) providing deterministic checks, source evidence grounding, consistency auditing, candidate reranking, LLM judge critique, and calibrated confidence scoring.",
    capabilities=[
        PluginCapability.OUTPUT_VALIDATION.value,
        PluginCapability.FACT_CHECKING.value,
        PluginCapability.RESULT_RERANKING.value,
        PluginCapability.CONSISTENCY_CHECKING.value,
        PluginCapability.CODE_VERIFICATION.value,
        PluginCapability.DATA_VERIFICATION.value,
        PluginCapability.SOURCE_EVIDENCE_CHECK.value,
        PluginCapability.CONFIDENCE_SCORING.value,
        PluginCapability.LLM_JUDGE.value,
        PluginCapability.FINAL_RESPONSE_VERIFICATION.value,
    ],
    input_schema_name="VerificationInput",
    output_schema_name="VerificationResult",
    author="Xeren Core Team",
    metadata={
        "category": "quality_assurance",
        "deterministic_first": True,
        "calibrated_scoring": True,
        "supported_statuses": ["verified", "partially_verified", "failed", "unverifiable"],
        "supports_llm_judge": True,
        "supports_reranking": True,
    },
)

__all__ = ["VERIFICATION_PLUGIN_MANIFEST"]
