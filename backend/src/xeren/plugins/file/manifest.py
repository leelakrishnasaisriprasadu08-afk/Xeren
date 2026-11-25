"""Manifest specification for Xeren Plugin #6: File Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

FILE_PLUGIN_MANIFEST = PluginManifest(
    name="file",
    version="0.1.0",
    description="Safe filesystem plugin providing controlled read, write, create, modify, delete, list, search, move, copy, and metadata inspection operations strictly within sandboxed workspace boundaries.",
    capabilities=[
        PluginCapability.FILE_READ.value,
        PluginCapability.FILE_WRITE.value,
        PluginCapability.FILE_CREATE.value,
        PluginCapability.FILE_MODIFY.value,
        PluginCapability.FILE_DELETE.value,
        PluginCapability.FILE_LIST.value,
        PluginCapability.FILE_SEARCH.value,
        PluginCapability.FILE_MOVE.value,
        PluginCapability.FILE_COPY.value,
        PluginCapability.FILE_METADATA.value,
    ],
    input_schema_name="FileInput",
    output_schema_name="FileResult",
    author="Xeren Core Team",
    metadata={
        "category": "filesystem",
        "sandboxed": True,
        "atomic_writes": True,
        "dry_run_supported": True,
        "best_effort_redaction": True,
        "default_max_size_bytes": 10 * 1024 * 1024,
    },
)

__all__ = ["FILE_PLUGIN_MANIFEST"]
