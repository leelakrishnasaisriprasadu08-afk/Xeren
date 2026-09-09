"""Manifest metadata for the Xeren Coding Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

CODING_PLUGIN_MANIFEST = PluginManifest(
    name="coding",
    version="0.1.0",
    description="Autonomous coding plugin providing code generation, syntax validation, static analysis, sandbox execution, testing, and multi-stage verification.",
    capabilities=[
        PluginCapability.CODE_EXECUTION.value,
        PluginCapability.CODE_GENERATION.value,
        PluginCapability.CODE_ANALYSIS.value,
        PluginCapability.SYNTAX_CHECKING.value,
        PluginCapability.TEST_EXECUTION.value,
        PluginCapability.CODE_VERIFICATION.value,
        PluginCapability.CODE_MODIFICATION.value,
    ],
    input_schema_name="CodingInput",
    output_schema_name="CodingResult",
    author="Xeren Core Team",
    metadata={
        "category": "code_intelligence_and_execution",
        "sandbox_enabled": True,
        "supported_languages": ["python", "javascript", "typescript"],
        "supports_verification": True,
    },
)

__all__ = ["CODING_PLUGIN_MANIFEST"]
