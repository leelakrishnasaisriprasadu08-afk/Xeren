"""Xeren Modular Plugin System."""

from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginCapability,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import (
    PluginError,
    PluginExecutionError,
    PluginHealthCheckError,
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)
from xeren.plugins.conversation import ConversationPlugin
from xeren.plugins.manager import PluginManager

__all__ = [
    "BasePlugin",
    "ConversationPlugin",
    "PluginCapability",
    "PluginHealthStatus",
    "HealthCheckResult",
    "PluginManifest",
    "PluginExecutionContext",
    "PluginExecutionResult",
    "PluginManager",
    "PluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "PluginExecutionError",
    "PluginTimeoutError",
    "PluginHealthCheckError",
]
