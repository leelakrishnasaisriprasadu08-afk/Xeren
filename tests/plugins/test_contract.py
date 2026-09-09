"""Unit tests for the reusable Xeren Plugin contract and base abstractions."""

from typing import Any, Dict, List, Optional, Type, Union
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
from xeren.plugins.errors import PluginValidationError


class DummyInput(BaseModel):
    value: str = Field(..., min_length=1)
    count: int = Field(default=1, ge=1)


class DummyOutput(BaseModel):
    echo: str
    repeated: List[str]


class DummyPlugin(BasePlugin):
    """Test plugin implementation."""

    def __init__(self, should_fail: bool = False, is_healthy: bool = True) -> None:
        self.should_fail = should_fail
        self.is_healthy = is_healthy
        self.initialized = False
        self.shutdown_called = False

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="dummy",
            version="1.0.0",
            description="Dummy test plugin",
            capabilities=[PluginCapability.CUSTOM.value],
            input_schema_name="DummyInput",
            output_schema_name="DummyOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return DummyInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return DummyOutput

    def initialize(self) -> None:
        self.initialized = True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        validated = self.validate_input(input_data)
        assert isinstance(validated, DummyInput)

        if self.should_fail:
            raise RuntimeError("Dummy execution failure")

        output = DummyOutput(
            echo=validated.value,
            repeated=[validated.value] * validated.count,
        )
        return PluginExecutionResult(
            plugin_name=self.name,
            success=True,
            output=output,
            latency_ms=1.5,
        )

    def health_check(self) -> HealthCheckResult:
        if not self.is_healthy:
            return HealthCheckResult(
                status=PluginHealthStatus.UNHEALTHY,
                details={"reason": "Simulated unhealthy state"},
                error="Service unavailable",
            )
        return super().health_check()


def test_plugin_properties() -> None:
    plugin = DummyPlugin()
    assert plugin.name == "dummy"
    assert plugin.version == "1.0.0"
    assert plugin.description == "Dummy test plugin"
    assert plugin.capabilities == ["custom"]
    assert plugin.input_schema is DummyInput
    assert plugin.output_schema is DummyOutput


def test_plugin_validation_success() -> None:
    plugin = DummyPlugin()
    # From model instance
    valid_model = DummyInput(value="hello", count=3)
    validated = plugin.validate_input(valid_model)
    assert isinstance(validated, DummyInput)
    assert validated.value == "hello"

    # From dictionary
    validated_dict = plugin.validate_input({"value": "world", "count": 2})
    assert isinstance(validated_dict, DummyInput)
    assert validated_dict.value == "world"

    # Output validation
    out = DummyOutput(echo="test", repeated=["test"])
    validated_out = plugin.validate_output(out)
    assert isinstance(validated_out, DummyOutput)
    assert validated_out.echo == "test"


def test_plugin_validation_failures() -> None:
    plugin = DummyPlugin()
    # Invalid type
    with pytest.raises(PluginValidationError):
        plugin.validate_input("invalid string")

    # Missing required field
    with pytest.raises(PluginValidationError):
        plugin.validate_input({"count": 5})

    # Failed bounds constraint
    with pytest.raises(PluginValidationError):
        plugin.validate_input({"value": "x", "count": 0})

    # Invalid output validation
    with pytest.raises(PluginValidationError):
        plugin.validate_output({"invalid": "data"})


def test_plugin_execute_sync() -> None:
    plugin = DummyPlugin()
    result = plugin.execute({"value": "test", "count": 2})
    assert result.success is True
    assert result.plugin_name == "dummy"
    assert isinstance(result.output, DummyOutput)
    assert result.output.echo == "test"
    assert len(result.output.repeated) == 2


@pytest.mark.asyncio
async def test_plugin_execute_async() -> None:
    plugin = DummyPlugin()
    result = await plugin.aexecute({"value": "async_test", "count": 3})
    assert result.success is True
    assert isinstance(result.output, DummyOutput)
    assert result.output.echo == "async_test"
    assert len(result.output.repeated) == 3


def test_plugin_health_check() -> None:
    plugin = DummyPlugin(is_healthy=True)
    health = plugin.health_check()
    assert health.status == PluginHealthStatus.HEALTHY
    assert health.details["name"] == "dummy"

    unhealthy_plugin = DummyPlugin(is_healthy=False)
    unhealthy_status = unhealthy_plugin.health_check()
    assert unhealthy_status.status == PluginHealthStatus.UNHEALTHY
    assert unhealthy_status.error == "Service unavailable"


@pytest.mark.asyncio
async def test_plugin_health_check_async() -> None:
    plugin = DummyPlugin(is_healthy=True)
    health = await plugin.ahealth_check()
    assert health.status == PluginHealthStatus.HEALTHY


def test_plugin_lifecycle_hooks() -> None:
    plugin = DummyPlugin()
    assert plugin.initialized is False
    assert plugin.shutdown_called is False

    plugin.initialize()
    assert plugin.initialized is True

    plugin.shutdown()
    assert plugin.shutdown_called is True
