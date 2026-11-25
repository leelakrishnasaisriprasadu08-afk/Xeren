"""Unit tests for Xeren PluginManager."""

import asyncio
import time
from typing import Any, Dict, Optional, Type, Union
import pytest
from pydantic import BaseModel, Field

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
    PluginExecutionError,
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)
from xeren.plugins.manager import PluginManager


class SampleInput(BaseModel):
    query: str


class SampleOutput(BaseModel):
    reply: str


class FastPlugin(BasePlugin):
    """Simple functional plugin for manager tests."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="fast",
            version="0.1.0",
            description="Fast test plugin",
            capabilities=[PluginCapability.CUSTOM.value],
            input_schema_name="SampleInput",
            output_schema_name="SampleOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return SampleInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return SampleOutput

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        validated = self.validate_input(input_data)
        return PluginExecutionResult(
            plugin_name=self.name,
            success=True,
            output=SampleOutput(reply=f"Processed: {validated.query}"),  # type: ignore
        )


class SlowPlugin(BasePlugin):
    """Simulates slow execution for timeout testing."""

    def __init__(self, delay_seconds: float = 1.0) -> None:
        self.delay_seconds = delay_seconds

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="slow",
            version="0.1.0",
            description="Slow plugin",
            capabilities=[PluginCapability.CUSTOM.value],
            input_schema_name="SampleInput",
            output_schema_name="SampleOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return SampleInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return SampleOutput

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        self.validate_input(input_data)
        time.sleep(self.delay_seconds)
        return PluginExecutionResult(plugin_name=self.name, success=True, output=SampleOutput(reply="Done"))

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        self.validate_input(input_data)
        await asyncio.sleep(self.delay_seconds)
        return PluginExecutionResult(plugin_name=self.name, success=True, output=SampleOutput(reply="Done"))


class FailingPlugin(BasePlugin):
    """Plugin that throws an exception during execution."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="failing",
            version="0.1.0",
            description="Failing plugin",
            capabilities=[],
            input_schema_name="SampleInput",
            output_schema_name="SampleOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return SampleInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return SampleOutput

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        raise ValueError("Critical execution failure inside plugin")


def test_manager_registration_and_lookup() -> None:
    manager = PluginManager()
    fast = FastPlugin()

    manager.register(fast)
    assert manager.has("fast") is True
    assert manager.has("FAST") is True  # Case insensitive
    assert manager.get("fast") is fast
    assert manager.list_names() == ["fast"]
    assert len(manager.list_plugins()) == 1

    # Duplicate registration without override fails
    with pytest.raises(PluginValidationError):
        manager.register(FastPlugin())

    # Duplicate registration with override succeeds
    manager.register(FastPlugin(), override=True)
    assert manager.has("fast") is True

    # Unregister
    removed = manager.unregister("fast")
    assert removed is not None
    assert manager.has("fast") is False
    assert manager.get("fast") is None


def test_manager_get_required_raises_not_found() -> None:
    manager = PluginManager()
    with pytest.raises(PluginNotFoundError):
        manager.get_required("nonexistent")


def test_manager_list_by_capability() -> None:
    manager = PluginManager([FastPlugin()])
    plugins = manager.list_by_capability("custom")
    assert len(plugins) == 1
    assert plugins[0].name == "fast"

    empty = manager.list_by_capability("nonexistent_capability")
    assert len(empty) == 0


def test_manager_execute_sync() -> None:
    manager = PluginManager([FastPlugin()])
    result = manager.execute("fast", {"query": "hello world"})
    assert result.success is True
    assert result.plugin_name == "fast"
    assert isinstance(result.output, SampleOutput)
    assert result.output.reply == "Processed: hello world"


@pytest.mark.asyncio
async def test_manager_execute_async() -> None:
    manager = PluginManager([FastPlugin()])
    result = await manager.aexecute("fast", SampleInput(query="async query"))
    assert result.success is True
    assert isinstance(result.output, SampleOutput)
    assert result.output.reply == "Processed: async query"


def test_manager_execute_invalid_input_raises_validation_error() -> None:
    manager = PluginManager([FastPlugin()])
    with pytest.raises(PluginValidationError):
        manager.execute("fast", {"wrong_field": 123})


def test_manager_execute_timeout_sync() -> None:
    manager = PluginManager([SlowPlugin(delay_seconds=0.5)])
    # Timeout after 0.1s
    result = manager.execute("slow", {"query": "wait"}, timeout=0.1)
    assert result.success is False
    assert "timed out" in (result.error or "")

    # Raise on timeout if flag requested
    with pytest.raises(PluginTimeoutError):
        manager.execute("slow", {"query": "wait"}, timeout=0.1, raise_on_error=True)


@pytest.mark.asyncio
async def test_manager_execute_timeout_async() -> None:
    manager = PluginManager([SlowPlugin(delay_seconds=0.5)])
    result = await manager.aexecute("slow", {"query": "wait"}, timeout=0.1)
    assert result.success is False
    assert "timed out" in (result.error or "")

    with pytest.raises(PluginTimeoutError):
        await manager.aexecute("slow", {"query": "wait"}, timeout=0.1, raise_on_error=True)


def test_manager_execute_error_handling() -> None:
    manager = PluginManager([FailingPlugin()])
    # By default, error is captured in result
    result = manager.execute("failing", {"query": "trigger error"})
    assert result.success is False
    assert "Critical execution failure" in (result.error or "")

    # If raise_on_error=True, raises PluginExecutionError
    with pytest.raises(PluginExecutionError):
        manager.execute("failing", {"query": "trigger error"}, raise_on_error=True)


def test_manager_health_check() -> None:
    manager = PluginManager([FastPlugin()])
    results = manager.health_check()
    assert "fast" in results
    assert results["fast"].status == PluginHealthStatus.HEALTHY

    single_result = manager.health_check("fast")
    assert "fast" in single_result


@pytest.mark.asyncio
async def test_manager_ahealth_check() -> None:
    manager = PluginManager([FastPlugin()])
    results = await manager.ahealth_check()
    assert "fast" in results
    assert results["fast"].status == PluginHealthStatus.HEALTHY


def test_manager_shutdown_all() -> None:
    manager = PluginManager([FastPlugin()])
    assert len(manager.list_names()) == 1
    manager.shutdown_all()
    assert len(manager.list_names()) == 0
