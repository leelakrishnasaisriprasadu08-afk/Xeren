"""Unit and integration tests for PlaywrightBrowserAdapter using controlled stubs and safety checks."""

from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from xeren.agent.browser import (
    BaseBrowserAdapter,
    BrowserSecurityError,
    BrowserSecurityManager,
    PlaywrightBrowserAdapter,
)
from xeren.agent.types import ActionResult, BrowserObservation

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    PlaywrightTimeoutError = Exception  # type: ignore


class StubLocator:
    """Stub locator simulating Playwright element interaction."""

    def __init__(self, selector: str, page: "StubPage") -> None:
        self.selector = selector
        self.page = page
        self.uploaded_files: List[str] = []
        self.typed_text: Optional[str] = None
        self.selected_value: Optional[str] = None

    @property
    def first(self) -> "StubLocator":
        return self

    async def click(self, timeout: Optional[int] = None) -> None:
        if self.selector == "#timeout-btn":
            raise PlaywrightTimeoutError("Click timed out")
        if self.selector == "#missing-btn":
            raise Exception("Element not found: unable to locate element")
        self.page.clicked.append(self.selector)

    async def fill(self, value: str, timeout: Optional[int] = None) -> None:
        if self.selector == "#timeout-input":
            raise PlaywrightTimeoutError("Fill timed out")
        if self.selector == "#missing-input":
            raise Exception("Element not found")
        self.typed_text = value

    async def select_option(self, value: Optional[str] = None, timeout: Optional[int] = None) -> List[str]:
        if self.selector == "#missing-select":
            raise Exception("Element not found")
        self.selected_value = value
        return [value or ""]

    async def inner_text(self, timeout: Optional[int] = None) -> str:
        return "Stubbed element text with token: sk-test12345678901234567890"

    async def inner_html(self, timeout: Optional[int] = None) -> str:
        return "<div><span>Inner HTML</span></div>"

    async def set_input_files(self, files: Any, timeout: Optional[int] = None) -> None:
        if self.selector == "#missing-upload":
            raise Exception("Element not found")
        self.uploaded_files.append(str(files))

    async def evaluate(self, expr: str) -> Any:
        return [{"col1": "val1", "col2": "val2"}]


class StubDownload:
    """Stub Playwright download artifact."""

    def __init__(self, filename: str = "report.csv") -> None:
        self.suggested_filename = filename
        self.saved_path: Optional[str] = None

    async def save_as(self, path: str) -> None:
        self.saved_path = path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("stub,download,data\n1,2,3\n", encoding="utf-8")


class StubDownloadContext:
    """Context manager stub for page.expect_download()."""

    def __init__(self, page: "StubPage", should_timeout: bool = False) -> None:
        self.page = page
        self.should_timeout = should_timeout
        self.download = StubDownload()

    async def __aenter__(self) -> "StubDownloadContext":
        if self.should_timeout:
            raise PlaywrightTimeoutError("Download timed out")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    @property
    async def value(self) -> StubDownload:
        return self.download


class StubResponse:
    def __init__(self, status: int = 200) -> None:
        self.status = status


class StubPage:
    """Controlled mock Page object implementing the Playwright Page contract."""

    def __init__(self, initial_url: str = "https://example.com") -> None:
        self.url = initial_url
        self._title = "Example Production Domain"
        self._is_closed = False
        self.clicked: List[str] = []
        self.scroll_log: List[str] = []
        self.fail_nav_timeout = False
        self.fail_nav_network = False
        self.fail_download_timeout = False

    async def title(self) -> str:
        return self._title

    def is_closed(self) -> bool:
        return self._is_closed

    async def close(self) -> None:
        self._is_closed = True

    def set_default_timeout(self, timeout: int) -> None:
        pass

    def set_default_navigation_timeout(self, timeout: int) -> None:
        pass

    async def goto(self, url: str, timeout: Optional[int] = None, wait_until: str = "domcontentloaded") -> StubResponse:
        if self.fail_nav_timeout:
            raise PlaywrightTimeoutError(f"Navigation timed out: {url}")
        if self.fail_nav_network:
            raise Exception("net::ERR_NAME_NOT_RESOLVED: Host not reachable")
        self.url = url
        return StubResponse(status=200)

    async def inner_text(self, selector: str, timeout: Optional[int] = None) -> str:
        return "Welcome to the real browser page. API key: sk-live12345678901234567890 and Bearer eyJhbGciOi"

    def locator(self, selector: str) -> StubLocator:
        return StubLocator(selector, self)

    def expect_download(self, timeout: Optional[int] = None) -> StubDownloadContext:
        return StubDownloadContext(self, should_timeout=self.fail_download_timeout)

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        self.scroll_log.append(expression)
        if "selectorList" in expression:
            return [
                {
                    "element_id": "el-0",
                    "tag_name": "button",
                    "selector": "#submit-btn",
                    "text": "Submit Form",
                    "element_type": None,
                    "is_visible": True,
                    "is_enabled": True,
                    "bounding_box": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0},
                },
                {
                    "element_id": "el-1",
                    "tag_name": "input",
                    "selector": "#username",
                    "text": "",
                    "element_type": "text",
                    "is_visible": True,
                    "is_enabled": True,
                    "bounding_box": {"x": 10.0, "y": 60.0, "width": 200.0, "height": 25.0},
                },
            ]
        if "a[href]" in expression:
            return [{"text": "Privacy Policy", "href": "https://example.com/privacy"}]
        if "forms" in expression:
            return [{"id": "login-form", "action": "/login", "method": "POST", "inputs": ["username", "password"]}]
        if "scrollX" in expression:
            return {"x": 0, "y": 250}
        return None


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(prefix="xeren_pw_test_") as tmpdir:
        ws = Path(tmpdir).resolve()
        upload_dir = ws / "uploads"
        download_dir = ws / "downloads"
        upload_dir.mkdir()
        download_dir.mkdir()
        yield ws, upload_dir, download_dir


@pytest.fixture
def stub_adapter(temp_workspace):
    ws, upload_dir, download_dir = temp_workspace
    sec_mgr = BrowserSecurityManager(
        allowed_workspace_dir=ws,
        allowed_upload_dir=upload_dir,
        allowed_download_dir=download_dir,
    )
    stub_page = StubPage()
    adapter = PlaywrightBrowserAdapter(security_manager=sec_mgr, page=stub_page)
    return adapter, stub_page, ws, upload_dir, download_dir


@pytest.mark.asyncio
async def test_playwright_adapter_navigation_success(stub_adapter):
    """Verify successful navigation on Playwright adapter."""
    adapter, stub_page, _, _, _ = stub_adapter
    result = await adapter.anavigate("https://example.com/dashboard")

    assert result.success is True
    assert result.error is None
    assert result.data["url"] == "https://example.com/dashboard"
    assert result.data["status_code"] == 200
    assert result.observation is not None
    assert result.observation.url == "https://example.com/dashboard"


@pytest.mark.asyncio
async def test_playwright_adapter_navigation_timeout(stub_adapter):
    """Verify navigation timeout becomes structured recoverable TIMEOUT error."""
    adapter, stub_page, _, _, _ = stub_adapter
    stub_page.fail_nav_timeout = True

    result = await adapter.anavigate("https://slow.example.com", timeout_ms=1000)

    assert result.success is False
    assert result.error_code == "TIMEOUT"
    assert result.error_category == "timeout"
    assert result.recoverable is True
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_playwright_adapter_navigation_network_failure(stub_adapter):
    """Verify network resolution failure translates to NETWORK_ERROR."""
    adapter, stub_page, _, _, _ = stub_adapter
    stub_page.fail_nav_network = True

    result = await adapter.anavigate("https://invalid-host.example")

    assert result.success is False
    assert result.error_code == "NETWORK_ERROR"
    assert result.recoverable is True


@pytest.mark.asyncio
async def test_playwright_adapter_forbidden_schemes_blocked(stub_adapter):
    """Verify dangerous schemes (javascript:, data:) are blocked before navigation."""
    adapter, _, _, _, _ = stub_adapter

    js_result = await adapter.anavigate("javascript:void(0)")
    assert js_result.success is False
    assert js_result.error_code == "SECURITY_VIOLATION"
    assert js_result.recoverable is False

    data_result = await adapter.anavigate("data:text/html,<h1>payload</h1>")
    assert data_result.success is False
    assert data_result.error_code == "SECURITY_VIOLATION"


@pytest.mark.asyncio
async def test_playwright_adapter_secret_redaction(stub_adapter):
    """Verify API keys and bearer tokens are redacted from observation text."""
    adapter, _, _, _, _ = stub_adapter
    obs = await adapter.aobserve()

    # Verify secret pattern was stripped
    assert "sk-live12345678901234567890" not in obs.text_content
    assert "[REDACTED_SECRET]" in obs.text_content
    assert len(obs.interactive_elements) == 2
    assert obs.forms[0]["id"] == "login-form"


@pytest.mark.asyncio
async def test_playwright_adapter_click_and_missing_element(stub_adapter):
    """Verify click execution and missing element error handling."""
    adapter, stub_page, _, _, _ = stub_adapter

    # 1. Valid click
    click_res = await adapter.aclick("#submit-btn")
    assert click_res.success is True
    assert "#submit-btn" in stub_page.clicked

    # 2. Timeout click
    timeout_res = await adapter.aclick("#timeout-btn")
    assert timeout_res.success is False
    assert timeout_res.error_code == "TIMEOUT"
    assert timeout_res.recoverable is True

    # 3. Missing element click
    missing_res = await adapter.aclick("#missing-btn")
    assert missing_res.success is False
    assert missing_res.error_code == "ELEMENT_NOT_FOUND"
    assert missing_res.recoverable is True


@pytest.mark.asyncio
async def test_playwright_adapter_type_and_redaction(stub_adapter):
    """Verify text input typing and preview secret masking."""
    adapter, _, _, _, _ = stub_adapter

    # 1. Typing regular text
    type_res = await adapter.atype_text("#username", "agent_user")
    assert type_res.success is True
    assert type_res.data["typed_length"] == len("agent_user")

    # 2. Typing sensitive password (preview must be redacted)
    secret_res = await adapter.atype_text("#password", "password: 'SuperSecret123'")
    assert secret_res.success is True
    assert "SuperSecret123" not in secret_res.data["preview"]
    assert "[REDACTED_SECRET]" in secret_res.data["preview"]


@pytest.mark.asyncio
async def test_playwright_adapter_select_and_scroll(stub_adapter):
    """Verify select option and scrolling evaluation."""
    adapter, stub_page, _, _, _ = stub_adapter

    sel_res = await adapter.aselect_option("#role-dropdown", "developer")
    assert sel_res.success is True
    assert sel_res.data["selected"] == ["developer"]

    scroll_res = await adapter.ascroll(direction="down", amount=400)
    assert scroll_res.success is True
    assert any("scrollBy(0, 400)" in expr for expr in stub_page.scroll_log)


@pytest.mark.asyncio
async def test_playwright_adapter_extract_content(stub_adapter):
    """Verify structured content extraction (text, html, table)."""
    adapter, _, _, _, _ = stub_adapter

    text_res = await adapter.aextract_content(extract_type="text")
    assert text_res.success is True
    assert "[REDACTED_SECRET]" in text_res.data["content"]

    table_res = await adapter.aextract_content(selector="#stats-table", extract_type="table")
    assert table_res.success is True
    assert isinstance(table_res.data["content"], list)


@pytest.mark.asyncio
async def test_playwright_adapter_upload_security_boundaries(stub_adapter):
    """Verify upload path traversal protection and valid file uploading."""
    adapter, _, ws, upload_dir, _ = stub_adapter

    # 1. Valid upload inside approved directory
    valid_file = upload_dir / "valid_data.json"
    valid_file.write_text("{}", encoding="utf-8")

    upload_res = await adapter.aupload_file("#file-input", valid_file)
    assert upload_res.success is True
    assert upload_res.data["file_name"] == "valid_data.json"

    # 2. Traversal attempt outside upload directory
    outside_file = ws / ".." / "evil_script.sh"
    outside_res = await adapter.aupload_file("#file-input", outside_file)
    assert outside_res.success is False
    assert outside_res.error_code == "SECURITY_VIOLATION"
    assert outside_res.recoverable is False


@pytest.mark.asyncio
async def test_playwright_adapter_download_security_boundaries(stub_adapter):
    """Verify download directory restriction and safe saving."""
    adapter, stub_page, ws, _, download_dir = stub_adapter

    # 1. Valid download inside approved directory
    target_dest = download_dir / "saved_report.csv"
    download_res = await adapter.adownload_file(
        trigger_selector="#download-btn",
        save_path=target_dest,
    )
    assert download_res.success is True
    assert target_dest.exists()
    assert target_dest.read_text(encoding="utf-8").startswith("stub,download")

    # 2. Directory traversal attempt during download
    bad_dest = ws / ".." / "escaped_download.csv"
    bad_res = await adapter.adownload_file(save_path=bad_dest)
    assert bad_res.success is False
    assert bad_res.error_code == "SECURITY_VIOLATION"
    assert bad_res.recoverable is False


@pytest.mark.asyncio
async def test_playwright_adapter_context_manager_cleanup(stub_adapter):
    """Verify async context manager invokes cleanup even after exceptions."""
    adapter, stub_page, _, _, _ = stub_adapter

    with pytest.raises(RuntimeError):
        async with adapter:
            assert adapter.is_active is True
            raise RuntimeError("Failure inside active browser block")

    # Adapter must be cleanly closed
    assert adapter._is_closed is True
    assert stub_page.is_closed() is True
