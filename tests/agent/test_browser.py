"""Tests for generic browser abstraction, MockBrowserAdapter, and BrowserPlugin."""

import pytest

from xeren.agent.browser.adapter import BrowserActionType, BrowserObservation
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.browser.plugin import BrowserInput, BrowserPlugin, BrowserResult
from xeren.plugins.manager import PluginManager


def test_mock_browser_adapter_primitives():
    """Verify all mock browser primitive actions operate in-memory."""
    browser = MockBrowserAdapter()

    # 1. Set custom page
    browser.set_page(
        url="https://test.local/form",
        title="Form Test",
        content="Fill this form",
        elements=[
            {"selector": "input#name", "text": ""},
            {"selector": "select#country", "text": "Select"},
            {"selector": "button#submit", "text": "Submit"},
        ],
    )

    # 2. Navigate
    obs = browser.navigate("https://test.local/form")
    assert obs.url == "https://test.local/form"
    assert obs.title == "Form Test"
    assert len(obs.elements) == 3

    # 3. Observe
    obs_current = browser.observe()
    assert obs_current.url == "https://test.local/form"

    # 4. Type
    browser.type("input#name", "Alice")
    assert browser.typed_inputs[-1] == {"selector": "input#name", "text": "Alice"}

    # 5. Select
    browser.select("select#country", "US")
    assert browser.selected_options[-1] == {"selector": "select#country", "value": "US"}

    # 6. Click
    browser.click("button#submit")
    assert "button#submit" in browser.clicked_selectors

    # 7. Scroll
    browser.scroll(direction="down", amount=300)
    assert browser.scroll_history[-1] == {"direction": "down", "amount": 300}

    # 8. Extract
    extracted = browser.extract(selector="button#submit")
    assert extracted["text"] == "Submit"

    # 9. Upload
    browser.upload("input#file", "/path/to/doc.pdf")
    assert browser.uploaded_files[-1] == {"selector": "input#file", "file_path": "/path/to/doc.pdf"}

    # 10. Download
    browser.set_download("https://test.local/file.bin", b"binary content")
    downloaded = browser.download("https://test.local/file.bin")
    assert downloaded == b"binary content"

    # 11. Close
    browser.close()
    assert browser.is_closed is True


def test_browser_plugin_contract_and_execution():
    """Verify BrowserPlugin integrates cleanly with PluginManager."""
    mock_adapter = MockBrowserAdapter()
    plugin = BrowserPlugin(adapter=mock_adapter)

    pm = PluginManager()
    pm.register(plugin)

    assert pm.has("browser")
    assert "browser_automation" in plugin.manifest.capabilities

    # Execute navigate
    res_nav = pm.execute("browser", {"action": "navigate", "url": "https://example.com"})
    assert res_nav.success is True
    assert isinstance(res_nav.output, BrowserResult)
    assert res_nav.output.action == "navigate"
    assert res_nav.output.observation is not None
    assert res_nav.output.observation.title == "Example Domain"

    # Execute type
    res_type = pm.execute("browser", {"action": "type", "selector": "#search", "text": "hello"})
    assert res_type.success is True
    assert mock_adapter.typed_inputs[-1]["text"] == "hello"

    # Execute unsupported action
    res_err = pm.execute("browser", {"action": "unsupported_action"})
    assert res_err.success is False
    assert "Unsupported browser action" in (res_err.error or "")


@pytest.mark.asyncio
async def test_browser_plugin_async_execution():
    """Verify asynchronous execution of browser operations."""
    plugin = BrowserPlugin(adapter=MockBrowserAdapter())
    pm = PluginManager()
    pm.register(plugin)

    res = await pm.aexecute("browser", {"action": "observe"})
    assert res.success is True
    assert isinstance(res.output, BrowserResult)
    assert res.output.observation is not None
