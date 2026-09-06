"""Unit tests for MockBrowserAdapter verifying all 10 required capabilities."""

from pathlib import Path
import tempfile
import pytest

from xeren.agent.browser import (
    BaseBrowserAdapter,
    BrowserSecurityManager,
    MockBrowserAdapter,
)
from xeren.agent.types import ActionResult, BrowserObservation


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(prefix="xeren_test_ws_") as tmpdir:
        ws = Path(tmpdir).resolve()
        upload_dir = ws / "uploads"
        download_dir = ws / "downloads"
        upload_dir.mkdir()
        download_dir.mkdir()
        yield ws, upload_dir, download_dir


@pytest.mark.asyncio
async def test_mock_adapter_inheritance_and_lifecycle():
    """Verify MockBrowserAdapter inherits BaseBrowserAdapter and manages lifecycle."""
    adapter = MockBrowserAdapter()
    assert isinstance(adapter, BaseBrowserAdapter)
    assert not adapter.is_initialized

    await adapter.ainitialize()
    assert adapter.is_initialized
    assert not adapter.is_closed

    await adapter.aclose()
    assert adapter.is_closed
    assert not adapter.is_initialized


@pytest.mark.asyncio
async def test_mock_navigation_success():
    """Capability 1: Verify successful navigation and observation payload."""
    adapter = MockBrowserAdapter()
    result = await adapter.anavigate("https://example.com")

    assert result.success is True
    assert result.error is None
    assert result.data is not None
    assert result.data["url"] == "https://example.com"
    assert result.data["title"] == "Example Domain"
    assert result.observation is not None
    assert isinstance(result.observation, BrowserObservation)
    assert result.observation.url == "https://example.com"
    assert "illustrative examples" in result.observation.text_content


@pytest.mark.asyncio
async def test_mock_navigation_failures():
    """Verify timeout, network failures, and forbidden schemes during navigation."""
    adapter = MockBrowserAdapter()

    # 1. Timeout failure
    adapter.fail_timeout = True
    timeout_res = await adapter.anavigate("https://example.com")
    assert timeout_res.success is False
    assert timeout_res.error_code == "TIMEOUT"
    assert timeout_res.recoverable is True
    adapter.fail_timeout = False

    # 2. Network failure
    adapter.fail_navigation = True
    nav_res = await adapter.anavigate("https://example.com")
    assert nav_res.success is False
    assert nav_res.error_code == "NAVIGATION_FAILED"
    assert nav_res.recoverable is True
    adapter.fail_navigation = False

    # 3. Forbidden URL scheme (e.g. javascript:)
    sec_res = await adapter.anavigate("javascript:alert(1)")
    assert sec_res.success is False
    assert sec_res.error_code == "SECURITY_VIOLATION"
    assert sec_res.recoverable is False


@pytest.mark.asyncio
async def test_mock_page_observation():
    """Capability 2: Verify page observation extracts title, text, elements, and scroll pos."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    obs = await adapter.aobserve()
    assert obs.url == "https://example.com"
    assert obs.title == "Example Domain"
    assert len(obs.interactive_elements) >= 3
    selectors = [e.selector for e in obs.interactive_elements]
    assert "#more-info" in selectors
    assert "input[name='q']" in selectors


@pytest.mark.asyncio
async def test_mock_click():
    """Capability 3: Verify click on elements and missing element handling."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    # Valid click
    click_res = await adapter.aclick("#more-info")
    assert click_res.success is True
    assert click_res.data is not None
    assert click_res.data["clicked"] == "#more-info"
    assert "#more-info" in adapter.clicked_elements

    # Missing element click
    missing_res = await adapter.aclick("#non-existent-button")
    assert missing_res.success is False
    assert missing_res.error_code == "ELEMENT_NOT_FOUND"
    assert missing_res.recoverable is True


@pytest.mark.asyncio
async def test_mock_typing():
    """Capability 4: Verify text typing and input sanitization."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    type_res = await adapter.atype_text("input[name='q']", "autonomous agent search")
    assert type_res.success is True
    assert type_res.data is not None
    assert type_res.data["typed_length"] == len("autonomous agent search")
    assert adapter.form_inputs["input[name='q']"] == "autonomous agent search"

    # Typing with missing element
    adapter.fail_missing_element = True
    fail_type = await adapter.atype_text("#missing", "test")
    assert fail_type.success is False
    assert fail_type.error_code == "ELEMENT_NOT_FOUND"
    adapter.fail_missing_element = False


@pytest.mark.asyncio
async def test_mock_select():
    """Capability 5: Verify option selection."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    sel_res = await adapter.aselect_option("#country-select", "US")
    assert sel_res.success is True
    assert sel_res.data is not None
    assert sel_res.data["selected_value"] == "US"
    assert adapter.form_inputs["#country-select"] == "US"


@pytest.mark.asyncio
async def test_mock_scrolling():
    """Capability 6: Verify scrolling in all directions."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    scroll_down = await adapter.ascroll(direction="down", amount=300)
    assert scroll_down.success is True
    assert adapter.scroll_pos["y"] == 300

    scroll_up = await adapter.ascroll(direction="up", amount=100)
    assert scroll_up.success is True
    assert adapter.scroll_pos["y"] == 200

    scroll_bot = await adapter.ascroll(direction="bottom")
    assert scroll_bot.success is True
    assert adapter.scroll_pos["y"] == 2500

    scroll_top = await adapter.ascroll(direction="top")
    assert scroll_top.success is True
    assert adapter.scroll_pos["y"] == 0


@pytest.mark.asyncio
async def test_mock_content_extraction():
    """Capability 7: Verify structured content extraction."""
    adapter = MockBrowserAdapter()
    await adapter.anavigate("https://example.com")

    extract_res = await adapter.aextract_content(extract_type="text")
    assert extract_res.success is True
    assert extract_res.data is not None
    assert "illustrative examples" in extract_res.data["content"]

    selector_res = await adapter.aextract_content(selector="h1", extract_type="text")
    assert selector_res.success is True
    assert selector_res.data is not None
    assert "h1" in selector_res.data["content"]


@pytest.mark.asyncio
async def test_mock_upload_and_download(temp_workspace):
    """Capabilities 8 & 9: Verify safe uploads and downloads through controlled paths."""
    ws, upload_dir, download_dir = temp_workspace
    sec_mgr = BrowserSecurityManager(
        allowed_workspace_dir=ws,
        allowed_upload_dir=upload_dir,
        allowed_download_dir=download_dir,
    )
    adapter = MockBrowserAdapter(security_manager=sec_mgr)
    await adapter.anavigate("https://example.com")

    # 1. Valid file upload
    test_upload = upload_dir / "dataset.csv"
    test_upload.write_text("x,y\n1,2\n", encoding="utf-8")

    upload_res = await adapter.aupload_file("input[type='file']", test_upload)
    assert upload_res.success is True
    assert upload_res.data is not None
    assert upload_res.data["file_name"] == "dataset.csv"

    # 2. Path traversal upload rejection
    traversal_path = upload_dir / ".." / "outside.txt"
    traversal_res = await adapter.aupload_file("input[type='file']", traversal_path)
    assert traversal_res.success is False
    assert traversal_res.error_code == "SECURITY_VIOLATION"
    assert traversal_res.recoverable is False

    # 3. Valid download
    download_res = await adapter.adownload_file(
        trigger_selector="#download-report",
        save_path=download_dir / "my_report.csv",
    )
    assert download_res.success is True
    assert (download_dir / "my_report.csv").exists()

    # 4. Download directory breakout rejection
    bad_download = ws / ".." / "escaped.csv"
    bad_res = await adapter.adownload_file(save_path=bad_download)
    assert bad_res.success is False
    assert bad_res.error_code == "SECURITY_VIOLATION"


def test_mock_synchronous_wrappers():
    """Capability 10: Verify synchronous wrappers work for compatibility."""
    adapter = MockBrowserAdapter()
    nav_res = adapter.navigate("https://example.com")
    assert nav_res.success is True

    click_res = adapter.click("#more-info")
    assert click_res.success is True

    type_res = adapter.type_text("input[name='q']", "sync typing")
    assert type_res.success is True

    adapter.close()
    assert adapter.is_closed
