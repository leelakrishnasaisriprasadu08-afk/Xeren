"""Manifest metadata for the Xeren Website Creation Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

WEBSITE_PLUGIN_MANIFEST = PluginManifest(
    name="website",
    version="0.1.0",
    description="Autonomous website creation plugin providing requirement analysis, project generation, file editing, structural and syntax validation, static security auditing, and safe preview.",
    capabilities=[
        PluginCapability.WEBSITE_REQUIREMENT_ANALYSIS.value,
        PluginCapability.WEBSITE_GENERATION.value,
        PluginCapability.WEBSITE_MODIFICATION.value,
        PluginCapability.WEBSITE_VALIDATION.value,
        PluginCapability.WEBSITE_SECURITY_CHECK.value,
        PluginCapability.WEBSITE_PREVIEW.value,
    ],
    input_schema_name="WebsiteInput",
    output_schema_name="WebsiteResult",
    author="Xeren Core Team",
    metadata={
        "category": "web_development",
        "default_stack": ["html", "css", "javascript"],
        "static_security_check": True,
        "preview_support": True,
    },
)

__all__ = ["WEBSITE_PLUGIN_MANIFEST"]
