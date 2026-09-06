"""Manifest metadata specification for the Xeren Automation / Task Plugin."""

from xeren.plugins.contract import PluginCapability, PluginManifest

AUTOMATION_PLUGIN_MANIFEST = PluginManifest(
    name="automation",
    version="0.1.0",
    description=(
        "Coordinates and orchestrates structured multi-step task automation workflows "
        "across Xeren plugins with DAG dependency management, deterministic scheduling, "
        "safe retries, failure isolation, and execution history."
    ),
    capabilities=[
        PluginCapability.TASK_CREATE.value,
        PluginCapability.TASK_PLAN.value,
        PluginCapability.TASK_EXECUTE.value,
        PluginCapability.TASK_PAUSE.value,
        PluginCapability.TASK_RESUME.value,
        PluginCapability.TASK_CANCEL.value,
        PluginCapability.TASK_STATUS.value,
        PluginCapability.TASK_RETRY.value,
        PluginCapability.TASK_DEPENDENCY_MANAGEMENT.value,
        PluginCapability.TASK_HISTORY.value,
    ],
    input_schema_name="AutomationInput",
    output_schema_name="AutomationResult",
    author="Xeren Team",
    metadata={
        "category": "task_automation",
        "orchestration_layer": True,
        "max_steps_default": 50,
        "default_timeout_seconds": 300.0,
    },
)

__all__ = ["AUTOMATION_PLUGIN_MANIFEST"]
