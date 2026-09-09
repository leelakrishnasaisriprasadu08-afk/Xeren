"""Error types for the Xeren modular plugin architecture."""

from typing import Optional


class PluginError(Exception):
    """Base exception for all plugin-related errors."""

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        raw_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.plugin_name = plugin_name
        self.raw_error = raw_error

    def __str__(self) -> str:
        prefix = f"[{self.plugin_name}] " if self.plugin_name else ""
        return f"{prefix}{self.message}"


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not registered in the PluginManager."""
    pass


class PluginValidationError(PluginError):
    """Raised when plugin input or output validation fails."""
    pass


class PluginExecutionError(PluginError):
    """Raised when an error occurs during plugin execution."""
    pass


class PluginTimeoutError(PluginError):
    """Raised when plugin execution exceeds the configured timeout limit."""
    pass


class PluginHealthCheckError(PluginError):
    """Raised when a plugin health check encounters a fatal failure."""
    pass


__all__ = [
    "PluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "PluginExecutionError",
    "PluginTimeoutError",
    "PluginHealthCheckError",
]
