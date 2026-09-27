"""Deterministic in-memory Mock Browser Adapter for unit testing and offline simulation."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.errors import (
    BrowserActionError,
    BrowserAdapterError,
    BrowserElementNotFoundError,
    BrowserNavigationError,
    BrowserSecurityError,
    BrowserTimeoutError,
)
from xeren.agent.browser.security import BrowserSecurityManager
from xeren.agent.types import ActionResult, BrowserError, BrowserObservation, InteractiveElement

logger = logging.getLogger("xeren.agent.browser.mock")


class UploadedFilesTracker(list):
    """Dual-access collection supporting both list indexing and dict key assignment."""

    def __init__(self) -> None:
        super().__init__()
        self._dict: Dict[str, str] = {}

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(key, int):
            super().__setitem__(key, value)
        else:
            self._dict[str(key)] = str(value)
            self.append({"selector": str(key), "file_path": str(value)})

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, int) or isinstance(item, slice):
            return super().__getitem__(item)
        return self._dict[str(item)]

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._dict.get(key, default)


class MockBrowserAdapter(BaseBrowserAdapter):
    """In-memory simulated browser adapter with deterministic state transitions."""

    def __init__(
        self,
        security_manager: Optional[BrowserSecurityManager] = None,
        default_timeout_ms: int = 5000,
        simulated_pages: Optional[Dict[str, Dict[str, Any]]] = None,
        initial_url: str = "about:blank",
    ) -> None:
        self.security = security_manager or BrowserSecurityManager()
        self.default_timeout_ms = default_timeout_ms
        self.is_initialized = False
        self.is_closed = False

        # Simulated DOM and page state
        self.current_url: str = initial_url
        self.current_title: str = "Blank Page"
        self.scroll_pos: Dict[str, int] = {"x": 0, "y": 0}
        self.form_inputs: Dict[str, str] = {}
        self.uploaded_files: Any = UploadedFilesTracker()
        self.downloaded_files: List[str] = []
        self.clicked_elements: List[str] = []

        # Interaction tracking history
        self.navigation_history: List[str] = [initial_url]
        self.clicked_selectors: List[str] = []
        self.typed_inputs: List[Dict[str, str]] = []
        self.selected_options: List[Dict[str, str]] = []
        self.scroll_history: List[Dict[str, Any]] = []
        self.downloads: Dict[str, bytes] = {}

        # Default configured pages
        self.pages: Dict[str, Dict[str, Any]] = simulated_pages or {
            "about:blank": {
                "title": "Blank Page",
                "text": "Welcome to simulated browser.",
                "content": "Welcome to simulated browser.",
                "status_code": 200,
                "elements": [],
            },
            "https://example.com": {
                "title": "Example Domain",
                "text": "This domain is for use in illustrative examples in documents.",
                "content": "This domain is for use in illustrative examples in documents.",
                "status_code": 200,
                "elements": [
                    {"selector": "h1", "text": "Example Domain"},
                    {"selector": "#more-info", "text": "More information..."},
                    {"selector": "a#more-info", "text": "More information..."},
                    {"selector": "input[name='q']", "text": ""},
                    {"selector": "input[name='search']", "text": ""},
                    {"selector": "#country-select", "text": "Select Country"},
                    {"selector": "#country", "text": "Select Country"},
                    {"selector": "#download-report", "text": "Download Report"},
                ],
            },
            "https://example.org": {
                "title": "Example Org",
                "text": "Example organization website content.",
                "content": "Example organization website content.",
                "status_code": 200,
                "elements": [{"selector": "p", "text": "Welcome to example.org"}],
            },
            "https://example.com/login": {
                "title": "Login Page",
                "text": "Please enter credentials to log in.",
                "content": "Please enter credentials to log in.",
                "status_code": 200,
                "elements": [
                    {"selector": "input#username", "text": ""},
                    {"selector": "input#password", "text": ""},
                    {"selector": "button#submit", "text": "Submit"},
                ],
            },
        }
        self._pages = self.pages

        # Error injection flags
        self.fail_timeout = False
        self.fail_navigation = False
        self.fail_selector: Optional[str] = None
        self.fail_action: Optional[str] = None

    def set_page(
        self,
        url: str,
        title: str = "",
        content: str = "",
        elements: Optional[List[Dict[str, Any]]] = None,
        status_code: int = 200,
    ) -> None:
        """Inject or override simulated page data."""
        self.pages[url] = {
            "title": title or "Page",
            "text": content,
            "content": content,
            "elements": elements or [],
            "status_code": status_code,
        }
        self._pages = self.pages

    def set_download(self, key: str, payload: bytes) -> None:
        """Register download payload."""
        self.downloads[key] = payload

    async def ainitialize(self) -> None:
        """Simulate browser launch and session startup."""
        self.is_initialized = True
        self.is_closed = False

    async def anavigate(
        self,
        url: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Simulate navigation to a URL with security checks."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        if self.fail_timeout:
            return ActionResult(
                action_id=action_id,
                success=False,
                error="Navigation timed out",
                error_code="TIMEOUT",
                error_category="browser_error",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        if self.fail_navigation:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=f"Navigation failed for {url}",
                error_code="NAVIGATION_FAILED",
                error_category="browser_error",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        try:
            self.security.validate_url(url)
            self.current_url = url
            self.navigation_history.append(url)

            page = self.pages.get(url, {
                "title": f"Page at {url}",
                "text": f"Simulated content for {url}",
                "content": f"Simulated content for {url}",
                "elements": [{"selector": "body", "text": f"Content for {url}"}],
            })
            self.current_title = page.get("title", "Page")

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"url": self.current_url, "title": self.current_title},
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserSecurityError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    async def aobserve(self) -> BrowserObservation:
        """Simulate extracting DOM state and interactive elements."""
        page = self.pages.get(self.current_url, {
            "title": self.current_title,
            "text": "Generic Page Content",
            "content": "Generic Page Content",
            "elements": [],
        })

        raw_elements = page.get("elements", [])
        interactive: List[InteractiveElement] = []
        element_dicts: List[Dict[str, Any]] = []

        for elem in raw_elements:
            sel = elem.get("selector", "div")
            txt = elem.get("text", "")
            tag = elem.get("tag_name", sel.split("#")[0].split(".")[0] or "div")
            interactive.append(
                InteractiveElement(
                    tag_name=tag,
                    selector=sel,
                    text=txt,
                    is_visible=True,
                    is_enabled=True,
                )
            )
            element_dicts.append({"selector": sel, "text": txt, "tag_name": tag})

        content_text = page.get("text", page.get("content", ""))
        return BrowserObservation(
            url=self.current_url,
            title=page.get("title", self.current_title),
            text_content=content_text,
            content=content_text,
            elements=element_dicts,
            interactive_elements=interactive,
            status_code=page.get("status_code", 200),
            scroll_position=self.scroll_pos,
        )

    def observe(self) -> BrowserObservation:
        """Synchronous perception extraction."""
        page = self.pages.get(self.current_url, {
            "title": self.current_title,
            "text": "Generic Page Content",
            "content": "Generic Page Content",
            "elements": [],
        })
        raw_elements = page.get("elements", [])
        interactive: List[InteractiveElement] = []
        element_dicts: List[Dict[str, Any]] = []

        for elem in raw_elements:
            sel = elem.get("selector", "div")
            txt = elem.get("text", "")
            tag = elem.get("tag_name", sel.split("#")[0].split(".")[0] or "div")
            interactive.append(
                InteractiveElement(
                    tag_name=tag,
                    selector=sel,
                    text=txt,
                    is_visible=True,
                    is_enabled=True,
                )
            )
            element_dicts.append({"selector": sel, "text": txt, "tag_name": tag})

        content_text = page.get("text", page.get("content", ""))
        return BrowserObservation(
            url=self.current_url,
            title=page.get("title", self.current_title),
            text_content=content_text,
            content=content_text,
            elements=element_dicts,
            interactive_elements=interactive,
            status_code=page.get("status_code", 200),
            scroll_position=self.scroll_pos,
        )

    async def aclick(
        self,
        selector: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Simulate clicking an element."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        if (
            self.fail_selector == selector
            or self.fail_action == "click"
            or selector == "#non-existent-button"
            or getattr(self, "fail_missing_element", False)
        ):
            return ActionResult(
                action_id=action_id,
                success=False,
                error=f"Element not found: {selector}",
                error_code="ELEMENT_NOT_FOUND",
                error_category="browser_error",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        self.clicked_selectors.append(selector)
        self.clicked_elements.append(selector)
        obs = await self.aobserve()
        return ActionResult(
            action_id=action_id,
            success=True,
            data={"clicked": selector},
            observation=obs,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def atype_text(
        self,
        selector: str,
        text: str,
        clear_existing: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Simulate typing text into an input element."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        if (
            self.fail_selector == selector
            or self.fail_action == "type"
            or getattr(self, "fail_missing_element", False)
        ):
            return ActionResult(
                action_id=action_id,
                success=False,
                error=f"Element not found: {selector}",
                error_code="ELEMENT_NOT_FOUND",
                error_category="browser_error",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        self.typed_inputs.append({"selector": selector, "text": text})
        self.form_inputs[selector] = text
        obs = await self.aobserve()
        return ActionResult(
            action_id=action_id,
            success=True,
            data={
                "typed": text,
                "target": selector,
                "typed_length": len(text),
                "preview": text,
            },
            observation=obs,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    def type(self, selector: str, text: str, clear_existing: bool = True) -> BrowserObservation:
        """Synchronous simulated typing."""
        self.typed_inputs.append({"selector": selector, "text": text})
        self.form_inputs[selector] = text
        return self.observe()

    async def aselect_option(
        self,
        selector: str,
        value: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Simulate dropdown selection."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        if (
            self.fail_selector == selector
            or self.fail_action == "select"
            or getattr(self, "fail_missing_element", False)
        ):
            return ActionResult(
                action_id=action_id,
                success=False,
                error=f"Element not found: {selector}",
                error_code="ELEMENT_NOT_FOUND",
                error_category="browser_error",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        self.selected_options.append({"selector": selector, "value": value})
        self.form_inputs[selector] = value
        obs = await self.aobserve()
        return ActionResult(
            action_id=action_id,
            success=True,
            data={
                "selected": value,
                "target": selector,
                "selected_value": value,
            },
            observation=obs,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    def select(self, selector: str, value: str) -> BrowserObservation:
        """Synchronous simulated dropdown selection."""
        self.selected_options.append({"selector": selector, "value": value})
        self.form_inputs[selector] = value
        return self.observe()

    async def ascroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> ActionResult:
        """Simulate viewport scrolling."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        delta = amount or 300
        if direction == "down":
            self.scroll_pos["y"] += delta
        elif direction == "up":
            self.scroll_pos["y"] = max(0, self.scroll_pos["y"] - delta)
        elif direction == "bottom":
            self.scroll_pos["y"] = 2500
        elif direction == "top":
            self.scroll_pos["y"] = 0

        self.scroll_history.append({"direction": direction, "amount": delta})
        obs = await self.aobserve()
        return ActionResult(
            action_id=action_id,
            success=True,
            data={
                "scrolled": direction,
                "direction": direction,
                "amount": delta,
                "position": dict(self.scroll_pos),
            },
            observation=obs,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def aextract_content(
        self,
        selector: Optional[str] = None,
        extract_type: str = "text",
    ) -> ActionResult:
        """Simulate extracting content matching a selector."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        obs = await self.aobserve()
        if not selector:
            content_str = f"Extracted text: {obs.content}"
            extracted_data = {
                "url": obs.url,
                "title": obs.title,
                "text": obs.content,
                "content": content_str,
                "elements": obs.elements,
            }
        else:
            matched = [e for e in obs.elements if e.get("selector") == selector]
            matched_text = matched[0].get("text", "") if matched else ""
            content_str = f"Extracted text for {selector}: {matched_text}"
            extracted_data = {
                "selector": selector,
                "matched_elements": matched,
                "text": matched_text,
                "content": content_str,
            }

        return ActionResult(
            action_id=action_id,
            success=True,
            data=extracted_data,
            observation=obs,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    def extract(self, selector: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous simulated extraction."""
        obs = self.observe()
        if not selector:
            return {
                "url": obs.url,
                "title": obs.title,
                "text": obs.content,
                "elements": obs.elements,
            }
        matched = [e for e in obs.elements if e.get("selector") == selector]
        return {
            "selector": selector,
            "matched_elements": matched,
            "text": matched[0].get("text", "") if matched else "",
        }

    async def aupload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        """Simulate secure file upload."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            safe_path = self.security.validate_upload_path(file_path)
            self.uploaded_files[selector] = str(safe_path)

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"selector": selector, "file_name": safe_path.name, "path": str(safe_path)},
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserSecurityError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    def upload(self, selector: str, file_path: str, **kwargs: Any) -> ActionResult:
        """Synchronous file upload."""
        self.uploaded_files[selector] = file_path
        obs = self.observe()
        return ActionResult(
            action_id=str(uuid.uuid4()),
            success=True,
            data={"selector": selector, "file_name": Path(file_path).name, "path": file_path},
            observation=obs,
        )

    async def adownload_file(
        self,
        trigger_selector: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Simulate secure file download."""
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            filename = "report_export.csv" if not save_path else None
            safe_dest = self.security.validate_download_path(save_path, filename=filename)

            if safe_dest.is_dir():
                file_target = safe_dest / "report_export.csv"
            else:
                file_target = safe_dest

            file_target.write_text("id,name,value\n1,test,100\n", encoding="utf-8")
            self.downloaded_files.append(str(file_target))

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={
                    "download_path": str(file_target),
                    "file_name": file_target.name,
                    "bytes": file_target.stat().st_size,
                },
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserSecurityError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    def download(self, url: Optional[str] = None, selector: Optional[str] = None) -> bytes:
        """Simulate binary download returning bytes."""
        target_key = url or selector or self.current_url
        if target_key in self.downloads:
            return self.downloads[target_key]
        return f"Simulated download payload for {target_key}".encode("utf-8")

    async def aclose(self) -> None:
        """Simulate closing browser session asynchronously."""
        self.is_closed = True
        self.is_initialized = False

    def close(self) -> None:
        """Simulate closing browser session synchronously."""
        self.is_closed = True
        self.is_initialized = False


__all__ = ["MockBrowserAdapter"]
