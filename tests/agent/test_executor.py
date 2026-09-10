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

import pytest
from unittest.mock import AsyncMock, MagicMock

from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.executor import Executor
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.types import ActionCategory, AgentAction, ActionResult


@pytest.fixture
def mock_browser():
    return MockBrowserAdapter()


@pytest.mark.asyncio
async def test_executor_navigate(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    action = AgentAction(
        action_id="act-nav",
        action_type="navigate",
        target="https://example.com",
    )
    result = await executor.aexecute(action)
    assert result.success is True
    assert result.data is not None
    assert result.data.get("url") == "https://example.com"


@pytest.mark.asyncio
async def test_executor_click_and_type(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    await mock_browser.anavigate("https://example.com")

    type_action = AgentAction(
        action_id="act-type",
        action_type="type",
        target="input[name='search']",
        parameters={"text": "autonomous agent", "clear_existing": True},
    )
    res_type = await executor.aexecute(type_action)
    assert res_type.success is True
    assert res_type.data is not None
    assert res_type.data.get("preview") == "autonomous agent"

    click_action = AgentAction(
        action_id="act-click",
        action_type="click",
        target="#more-info",
    )
    res_click = await executor.aexecute(click_action)
    assert res_click.success is True


@pytest.mark.asyncio
async def test_executor_select_and_scroll(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    await mock_browser.anavigate("https://example.com")

    select_action = AgentAction(
        action_id="act-sel",
        action_type="select",
        target="#country",
        parameters={"value": "US"},
    )
    res_select = await executor.aexecute(select_action)
    assert res_select.success is True
    assert res_select.data is not None
    assert res_select.data.get("selected_value") == "US"

    scroll_action = AgentAction(
        action_id="act-scroll",
        action_type="scroll",
        parameters={"direction": "down", "amount": 400},
    )
    res_scroll = await executor.aexecute(scroll_action)
    assert res_scroll.success is True
    assert res_scroll.data is not None
    assert res_scroll.data.get("direction") == "down"


@pytest.mark.asyncio
async def test_executor_extract(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    await mock_browser.anavigate("https://example.com")

    extract_action = AgentAction(
        action_id="act-ext",
        action_type="extract",
        target="h1",
        parameters={"extract_type": "text"},
    )
    result = await executor.aexecute(extract_action)
    assert result.success is True
    assert result.data is not None
    assert "Extracted text" in result.data.get("content", "")


@pytest.mark.asyncio
async def test_executor_upload_and_download(mock_browser, tmp_path):
    upload_file = tmp_path / "data.csv"
    upload_file.write_text("a,b,c\n1,2,3")

    download_dest = tmp_path / "out.pdf"

    mock_browser.security.upload_dir = tmp_path.resolve()
    mock_browser.security.download_dir = tmp_path.resolve()
    perm_mgr = PermissionManager(require_consequential_approval=False)
    executor = Executor(browser_adapter=mock_browser, permission_manager=perm_mgr)
    await mock_browser.anavigate("https://example.com")

    upload_action = AgentAction(
        action_id="act-up",
        action_type="upload",
        target="#file-input",
        parameters={"file_path": str(upload_file)},
    )
    res_up = await executor.aexecute(upload_action)
    assert res_up.success is True

    download_action = AgentAction(
        action_id="act-down",
        action_type="download",
        target="#download-report",
        parameters={"trigger_selector": "#download-report", "save_path": str(download_dest)},
    )
    res_down = await executor.aexecute(download_action)
    assert res_down.success is True


@pytest.mark.asyncio
async def test_executor_permission_denial(mock_browser):
    # Strict mode requires explicit confirmation for consequential actions
    perm_mgr = PermissionManager(mode=PermissionMode.STRICT)
    executor = Executor(browser_adapter=mock_browser, permission_manager=perm_mgr)

    consequential_action = AgentAction(
        action_id="act-danger",
        action_type="upload",
        target="#secret-uploader",
        parameters={"file_path": "/safe/path.txt"},
        category=ActionCategory.CONSEQUENTIAL,
        consequential=True,
    )
    result = await executor.aexecute(consequential_action)
    assert result.success is False
    assert result.error_code == "PERMISSION_DENIED"
    assert result.recoverable is False


@pytest.mark.asyncio
async def test_executor_invalid_action_type(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    action = AgentAction(
        action_id="act-bad",
        action_type="unsupported_quantum_jump",
    )
    result = await executor.aexecute(action)
    assert result.success is False
    assert result.error_code == "INVALID_ACTION"


@pytest.mark.asyncio
async def test_executor_browser_exception_handling():
    faulty_browser = MagicMock()
    faulty_browser.anavigate = AsyncMock(side_effect=RuntimeError("Browser process crashed"))
    executor = Executor(browser_adapter=faulty_browser)

    action = AgentAction(
        action_id="act-fail",
        action_type="navigate",
        target="https://example.com",
    )
    result = await executor.aexecute(action)
    assert result.success is False
    assert result.error_code == "EXECUTION_ERROR"
    assert result.error is not None and "Browser process crashed" in result.error
    assert result.recoverable is True


def test_executor_sync_wrapper(mock_browser):
    executor = Executor(browser_adapter=mock_browser)
    action = AgentAction(
        action_id="act-sync",
        action_type="navigate",
        target="https://example.com",
    )
    result = executor.execute(action)
    assert result.success is True
    assert result.data is not None
    assert result.data.get("url") == "https://example.com"
