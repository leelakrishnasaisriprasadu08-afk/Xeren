"""Plugin Manager for registration, discovery, validation, lifecycle, and execution of Xeren plugins."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel

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
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)

logger = logging.getLogger("xeren.plugins.manager")


class PluginManager:
    """Manages the registry, lifecycle, health, and execution of Xeren plugins."""

    def __init__(self, plugins: Optional[Sequence[BasePlugin]] = None) -> None:
        self._plugins: Dict[str, BasePlugin] = {}
        if plugins:
            for plugin in plugins:
                self.register(plugin)

    def register(self, plugin: BasePlugin, override: bool = False) -> None:
        """Register a plugin instance with the manager."""
        name = plugin.name.lower()
        if name in self._plugins and not override:
            raise PluginValidationError(
                f"Plugin with name '{name}' is already registered.",
                plugin_name=name,
            )
        plugin.initialize()
        self._plugins[name] = plugin
        logger.info("Registered plugin: %s v%s (capabilities: %s)", name, plugin.version, plugin.capabilities)

    def unregister(self, name: str) -> Optional[BasePlugin]:
        """Unregister and shutdown a plugin by name."""
        key = name.lower()
        plugin = self._plugins.pop(key, None)
        if plugin:
            try:
                plugin.shutdown()
            except Exception as err:
                logger.warning("Error while shutting down plugin '%s': %s", key, err)
            logger.info("Unregistered plugin: %s", key)
        return plugin

    def get(self, name: str) -> Optional[BasePlugin]:
        """Retrieve a registered plugin by name."""
        return self._plugins.get(name.lower())

    def get_required(self, name: str) -> BasePlugin:
        """Retrieve a registered plugin or raise PluginNotFoundError."""
        plugin = self.get(name)
        if plugin is None:
            raise PluginNotFoundError(
                f"Plugin '{name}' is not registered. Available plugins: {self.list_names()}",
                plugin_name=name,
            )
        return plugin

    def has(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name.lower() in self._plugins

    def list_names(self) -> List[str]:
        """List all registered plugin names."""
        return sorted(list(self._plugins.keys()))

    def list_plugins(self) -> List[PluginManifest]:
        """List manifests of all registered plugins."""
        return [plugin.manifest for plugin in self._plugins.values()]

    def list_by_capability(self, capability: Union[PluginCapability, str]) -> List[BasePlugin]:
        """Find all registered plugins declaring a specific capability."""
        cap_str = capability if isinstance(capability, str) else capability.value
        return [p for p in self._plugins.values() if cap_str in p.capabilities]

    def get_by_capability(self, capability: Union[PluginCapability, str]) -> List[BasePlugin]:
        """Alias for list_by_capability."""
        return self.list_by_capability(capability)

    def execute(
        self,
        name: str,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
    ) -> PluginExecutionResult:
        """Synchronously execute a named plugin with input validation and timeout enforcement."""
        plugin = self.get_required(name)
        ctx = context or PluginExecutionContext()

        # Effective timeout
        effective_timeout = timeout or ctx.timeout_seconds
        start_time = time.perf_counter()

        try:
            # 1. Validate input
            validated_input = plugin.validate_input(input_data)

            # 2. Execute with optional timeout
            if effective_timeout is not None and effective_timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(plugin.execute, validated_input, ctx)
                    try:
                        result = future.result(timeout=effective_timeout)
                    except FuturesTimeoutError as err:
                        msg = f"Plugin '{name}' execution timed out after {effective_timeout:.2f}s"
                        logger.error(msg)
                        if raise_on_error:
                            raise PluginTimeoutError(msg, plugin_name=name, raw_error=err) from err
                        return PluginExecutionResult(
                            plugin_name=name,
                            success=False,
                            error=msg,
                            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                            metadata={"timeout_seconds": effective_timeout},
                        )
            else:
                result = plugin.execute(validated_input, ctx)

            # 3. Validate output if successful
            if result.success and result.output is not None:
                plugin.validate_output(result.output)

            return result

        except (PluginNotFoundError, PluginValidationError):
            raise
        except PluginTimeoutError:
            if raise_on_error:
                raise
            return PluginExecutionResult(
                plugin_name=name,
                success=False,
                error=f"Plugin '{name}' execution timed out",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
        except Exception as err:
            logger.exception("Plugin '%s' execution failed: %s", name, err)
            if raise_on_error:
                raise PluginExecutionError(
                    f"Execution failed for plugin '{name}': {err}",
                    plugin_name=name,
                    raw_error=err,
                ) from err
            return PluginExecutionResult(
                plugin_name=name,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

    async def aexecute(
        self,
        name: str,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
    ) -> PluginExecutionResult:
        """Asynchronously execute a named plugin with input validation and timeout enforcement."""
        plugin = self.get_required(name)
        ctx = context or PluginExecutionContext()
        effective_timeout = timeout or ctx.timeout_seconds
        start_time = time.perf_counter()

        try:
            validated_input = plugin.validate_input(input_data)

            if effective_timeout is not None and effective_timeout > 0:
                try:
                    result = await asyncio.wait_for(
                        plugin.aexecute(validated_input, ctx),
                        timeout=effective_timeout,
                    )
                except asyncio.TimeoutError as err:
                    msg = f"Plugin '{name}' execution timed out after {effective_timeout:.2f}s"
                    logger.error(msg)
                    if raise_on_error:
                        raise PluginTimeoutError(msg, plugin_name=name, raw_error=err) from err
                    return PluginExecutionResult(
                        plugin_name=name,
                        success=False,
                        error=msg,
                        latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                        metadata={"timeout_seconds": effective_timeout},
                    )
            else:
                result = await plugin.aexecute(validated_input, ctx)

            if result.success and result.output is not None:
                plugin.validate_output(result.output)

            return result

        except (PluginNotFoundError, PluginValidationError):
            raise
        except PluginTimeoutError:
            if raise_on_error:
                raise
            return PluginExecutionResult(
                plugin_name=name,
                success=False,
                error=f"Plugin '{name}' execution timed out",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
        except Exception as err:
            logger.exception("Plugin '%s' async execution failed: %s", name, err)
            if raise_on_error:
                raise PluginExecutionError(
                    f"Async execution failed for plugin '{name}': {err}",
                    plugin_name=name,
                    raw_error=err,
                ) from err
            return PluginExecutionResult(
                plugin_name=name,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

    def health_check(self, name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Perform synchronous health checks on one or all plugins."""
        if name:
            plugin = self.get_required(name)
            return {plugin.name: plugin.health_check()}
        return {p.name: p.health_check() for p in self._plugins.values()}

    async def ahealth_check(self, name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Perform asynchronous health checks on one or all plugins."""
        if name:
            plugin = self.get_required(name)
            return {plugin.name: await plugin.ahealth_check()}

        results: Dict[str, HealthCheckResult] = {}
        for p in self._plugins.values():
            results[p.name] = await p.ahealth_check()
        return results

    def shutdown_all(self) -> None:
        """Shutdown all registered plugins."""
        for name in list(self._plugins.keys()):
            self.unregister(name)


__all__ = ["PluginManager"]
