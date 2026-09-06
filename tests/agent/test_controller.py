"""End-to-end tests for AgentController driving autonomous work loops."""

import pytest

from xeren.agent.browser import MockBrowserAdapter, PlaywrightBrowserAdapter
from xeren.agent.controller import AgentController
from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.recovery import RecoveryManager
from xeren.agent.types import AgentAction, AgentStatus


@pytest.mark.asyncio
async def test_agent_controller_end_to_end_mock_run():
    """Verify autonomous execution of a multi-step web browsing task."""
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, max_steps=10)

    state = await controller.arun("Browse example.com and extract information")

    assert state.status == AgentStatus.COMPLETED
    assert state.step_count >= 2
    assert len(state.history) >= 2
    assert state.last_observation is not None
    assert state.last_observation.url == "https://example.com"
    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_recovery_integration():
    """Verify controller executes recovery action when a step fails."""
    browser = MockBrowserAdapter()
    # Trigger transient timeout on first navigation
    browser.fail_timeout = True

    controller = AgentController(browser_adapter=browser, max_steps=5)

    # Execute single step
    state = await controller.arun("Navigate to https://example.com", max_steps=1)
    # Failure occurred and recovery was recorded in history
    assert len(state.history) >= 1
    action, result = state.history[0]
    assert result.success is False
    assert result.error_code == "TIMEOUT"

    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_permission_enforcement():
    """Verify controller pauses or fails when consequential action lacks permission."""
    browser = MockBrowserAdapter()
    pm = PermissionManager(mode=PermissionMode.STRICT)  # Blocks interactive and consequential
    controller = AgentController(browser_adapter=browser, permission_manager=pm, max_steps=3)

    state = await controller.arun("Navigate to https://example.com", max_steps=1)

    # Step was blocked by permission manager
    assert len(state.history) >= 1
    _, result = state.history[0]
    assert result.success is False
    assert result.error_code == "PERMISSION_DENIED"

    await controller.aclose()


@pytest.mark.asyncio
async def test_agent_controller_adapter_switching():
    """Verify switching active browser adapter dynamically."""
    mock_browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=mock_browser)

    assert controller.browser is mock_browser

    # Switch to another adapter
    new_mock = MockBrowserAdapter()
    controller.set_browser_adapter(new_mock)
    assert controller.browser is new_mock
    assert controller.executor.browser is new_mock
    assert controller.observer.browser is new_mock

    await controller.aclose()


def test_agent_controller_sync_wrapper():
    """Verify synchronous run wrapper functions correctly."""
    browser = MockBrowserAdapter()
    controller = AgentController(browser_adapter=browser, max_steps=5)

    state = controller.run("Navigate to https://example.com and observe")
    assert state.status == AgentStatus.COMPLETED
    assert state.step_count >= 1
    controller.close()
