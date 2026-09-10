"""Tests for DefaultObserver."""

import pytest

from xeren.agent.actions import Action, ActionResult
from xeren.agent.observer import DefaultObserver
from xeren.agent.state import TaskState


def test_observer_captures_successful_outcome():
    """Verify observer produces detailed observation on success."""
    observer = DefaultObserver()
    action = Action(target="research", parameters={"query": "Xeren framework"}, description="Initial search")
    result = ActionResult(
        action_id=action.action_id,
        success=True,
        output="Summary of Xeren framework",
        latency_ms=45.2,
        artifacts={"summary.txt": "Xeren"},
    )
    state = TaskState(goal="Research Xeren")

    obs = observer.observe(action, result, state)

    assert obs.action_id == action.action_id
    assert obs.success is True
    assert "completed successfully" in obs.summary
    assert "Initial search" in obs.summary
    assert obs.artifacts_discovered == {"summary.txt": "Xeren"}
    assert obs.metadata["latency_ms"] == 45.2


def test_observer_captures_failed_outcome():
    """Verify observer captures failure reason and error details."""
    observer = DefaultObserver()
    action = Action(target="coding", parameters={"operation": "execute"})
    result = ActionResult(
        action_id=action.action_id,
        success=False,
        error="Execution sandbox timeout",
        latency_ms=3000.0,
    )
    state = TaskState(goal="Run code")

    obs = observer.observe(action, result, state)

    assert obs.success is False
    assert "failed: Execution sandbox timeout" in obs.summary
    assert obs.error == "Execution sandbox timeout"

import pytest

from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.observer import Observer
from xeren.agent.types import ActionResult, AgentAction, AgentState, BrowserObservation


@pytest.mark.asyncio
async def test_observer_aobserve():
    mock_browser = MockBrowserAdapter()
    await mock_browser.anavigate("https://example.com")
    observer = Observer(browser_adapter=mock_browser)

    obs = await observer.aobserve()
    assert isinstance(obs, BrowserObservation)
    assert obs.url == "https://example.com"
    assert obs.title == "Example Domain"
    assert len(obs.interactive_elements) > 0


def test_observer_update_state_success():
    mock_browser = MockBrowserAdapter()
    observer = Observer(browser_adapter=mock_browser)

    state = AgentState(
        session_id="s1",
        task="Test observation",
        plan=["Navigate to https://example.com"],
        step_count=0,
    )
    action = AgentAction(action_id="act-1", action_type="navigate", target="https://example.com")
    obs = BrowserObservation(url="https://example.com", title="Example Domain")
    result = ActionResult(action_id="act-1", success=True, data={"status": "ok"}, observation=obs)

    updated_state = observer.update_state(state, action, result)
    assert updated_state.step_count == 1
    assert len(updated_state.history) == 1
    assert updated_state.last_observation == obs
    assert updated_state.memory.get("step_1_result") == {"status": "ok"}


def test_observer_update_state_failure():
    mock_browser = MockBrowserAdapter()
    observer = Observer(browser_adapter=mock_browser)

    state = AgentState(
        session_id="s2",
        task="Test failure handling",
        plan=["Click button"],
        step_count=0,
    )
    action = AgentAction(action_id="act-2", action_type="click", target="#missing")
    result = ActionResult(action_id="act-2", success=False, error="Element not found")

    updated_state = observer.update_state(state, action, result)
    assert updated_state.step_count == 0
    assert len(updated_state.history) == 1
    assert "step_0_result" not in updated_state.memory


def test_observer_adapter_switch():
    browser1 = MockBrowserAdapter()
    browser2 = MockBrowserAdapter()
    observer = Observer(browser_adapter=browser1)
    assert observer.browser is browser1

    observer.set_browser_adapter(browser2)
    assert observer.browser is browser2

