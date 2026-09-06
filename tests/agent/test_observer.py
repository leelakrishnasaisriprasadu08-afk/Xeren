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
