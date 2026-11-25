"""Manifest metadata for the Xeren Data Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

DATA_PLUGIN_MANIFEST = PluginManifest(
    name="data",
    version="0.1.0",
    description="Modular Data Plugin providing dataset ingestion, inspection, cleaning, transformation, statistical analysis, visualization, and integrity verification.",
    capabilities=[
        PluginCapability.DATA_INGESTION.value,
        PluginCapability.DATA_INSPECTION.value,
        PluginCapability.DATA_CLEANING.value,
        PluginCapability.DATA_TRANSFORMATION.value,
        PluginCapability.DATA_ANALYSIS.value,
        PluginCapability.DATA_VISUALIZATION.value,
        PluginCapability.DATA_VERIFICATION.value,
    ],
    input_schema_name="DataInput",
    output_schema_name="DataResult",
    author="Xeren Core Team",
    metadata={
        "category": "data_intelligence",
        "supported_formats": ["csv", "json", "dict"],
        "supports_adapters": True,
    },
)

__all__ = ["DATA_PLUGIN_MANIFEST"]
