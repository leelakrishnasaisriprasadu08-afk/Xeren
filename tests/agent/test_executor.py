"""Tests for AgentExecutor integrating with existing PluginManager."""

import pytest

from xeren.agent.actions import Action, ActionResult
from xeren.agent.executor import AgentExecutor
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin


def test_executor_routes_to_plugin_manager():
    """Verify AgentExecutor calls existing plugins via PluginManager."""
    pm = PluginManager()
    pm.register(CodingPlugin())
    executor = AgentExecutor(plugin_manager=pm)

    action = Action(
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "def foo(): pass"},
    )
    result = executor.execute(action)

    assert result.success is True
    assert result.error is None
    assert result.action_id == action.action_id
    assert result.output is not None
    assert getattr(result.output, "syntax_valid", None) is True


def test_executor_unregistered_plugin_failure_isolation():
    """Verify calling an unregistered plugin returns failure without crashing."""
    pm = PluginManager()
    executor = AgentExecutor(plugin_manager=pm)

    action = Action(target="non_existent_plugin", parameters={})
    result = executor.execute(action)

    assert result.success is False
    assert "not registered" in (result.error or "")
    assert result.metadata.get("error_type") == "PluginNotFoundError"


def test_executor_extracts_artifacts():
    """Verify AgentExecutor automatically extracts code and data artifacts."""
    pm = PluginManager()
    pm.register(CodingPlugin())
    executor = AgentExecutor(plugin_manager=pm)

    action = Action(
        target="coding",
        parameters={"operation": "generate", "task": "Write hello world in python"},
    )
    result = executor.execute(action)

    assert result.success is True
    # Artifacts dictionary should capture generated files
    assert len(result.artifacts) >= 1
    file_key = list(result.artifacts.keys())[0]
    assert "code:" in file_key


@pytest.mark.asyncio
async def test_executor_aexecute():
    """Verify asynchronous action execution via aexecute."""
    pm = PluginManager()
    pm.register(CodingPlugin())
    executor = AgentExecutor(plugin_manager=pm)

    action = Action(
        target="coding",
        parameters={"operation": "syntax_check", "source_code": "x = 42"},
    )
    result = await executor.aexecute(action)

    assert result.success is True
    assert result.output is not None
    assert getattr(result.output, "syntax_valid", None) is True
