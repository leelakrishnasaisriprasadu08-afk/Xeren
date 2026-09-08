 feature/core-architecture
"""Deterministic in-memory MockBrowserAdapter for tests and offline operation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from xeren.agent.browser.adapter import BaseBrowserAdapter, BrowserObservation

logger = logging.getLogger("xeren.agent.browser.mock")


class MockBrowserAdapter(BaseBrowserAdapter):
    """Deterministic, pure in-memory browser simulation.

    Allows injecting page definitions, tracking user interactions, and testing
    browser workflows without network access or headless browser binaries.
    """

    def __init__(self, initial_url: str = "about:blank") -> None:
        self.current_url: str = initial_url
        self.is_closed: bool = False

        # In-memory page registry: url -> page attributes
        self._pages: Dict[str, Dict[str, Any]] = {
            "about:blank": {
                "title": "Blank Page",
                "content": "<html><body></body></html>",
                "status_code": 200,

"""Deterministic in-memory Mock Browser Adapter for unit testing and offline simulation."""

import asyncio
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


class MockBrowserAdapter(BaseBrowserAdapter):
    """In-memory simulated browser adapter with deterministic state transitions."""

    def __init__(
        self,
        security_manager: Optional[BrowserSecurityManager] = None,
        default_timeout_ms: int = 5000,
        simulated_pages: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.security = security_manager or BrowserSecurityManager()
        self.default_timeout_ms = default_timeout_ms
        self.is_initialized = False
        self.is_closed = False

        # Simulated DOM and page state
        self.current_url: str = "about:blank"
        self.current_title: str = "Blank Page"
        self.scroll_pos: Dict[str, int] = {"x": 0, "y": 0}
        self.form_inputs: Dict[str, str] = {}
        self.uploaded_files: Dict[str, str] = {}
        self.downloaded_files: List[str] = []
        self.clicked_elements: List[str] = []

        # Configured pages for multi-page simulation
        self.pages: Dict[str, Dict[str, Any]] = simulated_pages or {
            "about:blank": {
                "title": "Blank Page",
                "text": "Welcome to simulated browser.",
 main
                "elements": [],
            },
            "https://example.com": {
                "title": "Example Domain",
 feature/core-architecture
                "content": "Example Domain: Illustrative examples.",
                "status_code": 200,
                "elements": [
                    {"selector": "h1", "text": "Example Domain"},
                    {"selector": "a#more-info", "text": "More information..."},
                ],
            },
        }

        # Interaction tracking history
        self.navigation_history: List[str] = [initial_url]
        self.clicked_selectors: List[str] = []
        self.typed_inputs: List[Dict[str, str]] = []
        self.selected_options: List[Dict[str, str]] = []
        self.scroll_history: List[Dict[str, Any]] = []
        self.uploaded_files: List[Dict[str, str]] = []
        self.downloads: Dict[str, bytes] = {}

    def set_page(
        self,
        url: str,
        title: str = "",
        content: str = "",
        elements: Optional[List[Dict[str, Any]]] = None,
        status_code: int = 200,
    ) -> None:
        """Register or override a simulated page."""
        self._pages[url] = {
            "title": title,
            "content": content,
            "elements": elements or [],
            "status_code": status_code,
        }

    def set_download(self, key: str, data: bytes) -> None:
        """Register simulated downloadable content."""
        self.downloads[key] = data

    def navigate(self, url: str) -> BrowserObservation:
        """Navigate to a URL in memory."""
        self.current_url = url
        self.navigation_history.append(url)
        logger.debug("MockBrowser navigate to: %s", url)
        return self.observe()

    def observe(self) -> BrowserObservation:
        """Return observation of the current mock page."""
        page_info = self._pages.get(
            self.current_url,
            {
                "title": f"Page at {self.current_url}",
                "content": f"Simulated content for {self.current_url}",
                "status_code": 200,
                "elements": [],
            },
        )
        return BrowserObservation(
            url=self.current_url,
            title=page_info.get("title", ""),
            content=page_info.get("content", ""),
            status_code=page_info.get("status_code", 200),
            elements=page_info.get("elements", []),
            metadata={"history_length": len(self.navigation_history)},
        )

    def click(self, selector: str) -> BrowserObservation:
        """Simulate clicking an element."""
        self.clicked_selectors.append(selector)
        logger.debug("MockBrowser clicked selector: %s", selector)
        # Check if clicked selector triggers navigation in mock pages
        return self.observe()

    def type(self, selector: str, text: str) -> BrowserObservation:
        """Simulate typing text into an element."""
        self.typed_inputs.append({"selector": selector, "text": text})
        logger.debug("MockBrowser typed '%s' into selector '%s'", text, selector)
        return self.observe()

    def select(self, selector: str, value: str) -> BrowserObservation:
        """Simulate choosing a dropdown option."""
        self.selected_options.append({"selector": selector, "value": value})
        logger.debug("MockBrowser selected '%s' on selector '%s'", value, selector)
        return self.observe()

    def scroll(self, direction: str = "down", amount: int = 500) -> BrowserObservation:
        """Simulate scrolling."""
        self.scroll_history.append({"direction": direction, "amount": amount})
        logger.debug("MockBrowser scrolled %s by %d px", direction, amount)
        return self.observe()

    def extract(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Simulate extracting content matching a selector."""
        obs = self.observe()
        if not selector:
            return {
                "url": obs.url,
                "title": obs.title,
                "text": obs.content,
                "elements": obs.elements,
            }

        # Filter elements by selector
        matched = [e for e in obs.elements if e.get("selector") == selector]
        return {
            "selector": selector,
            "matched_elements": matched,
            "text": matched[0].get("text", "") if matched else "",
        }

    def upload(self, selector: str, file_path: str) -> BrowserObservation:
        """Simulate file upload."""
        self.uploaded_files.append({"selector": selector, "file_path": file_path})
        logger.debug("MockBrowser uploaded file '%s' to '%s'", file_path, selector)
        return self.observe()

    def download(self, url: Optional[str] = None, selector: Optional[str] = None) -> bytes:
        """Simulate binary download."""
        target_key = url or selector or self.current_url
        if target_key in self.downloads:
            return self.downloads[target_key]
        return f"Simulated download payload for {target_key}".encode("utf-8")

    def close(self) -> None:
        """Simulate closing browser."""
        self.is_closed = True
        logger.debug("MockBrowser closed")

                "text": "This domain is for use in illustrative examples in documents.",
                "elements": [
                    InteractiveElement(
                        element_id="btn-more",
                        tag_name="a",
                        selector="#more-info",
                        text="More information...",
                    ),
                    InteractiveElement(
                        element_id="input-search",
                        tag_name="input",
                        selector="input[name='q']",
                        element_type="text",
                    ),
                    InteractiveElement(
                        element_id="select-country",
                        tag_name="select",
                        selector="#country-select",
                    ),
                    InteractiveElement(
                        element_id="file-upload",
                        tag_name="input",
                        selector="input[type='file']",
                        element_type="file",
                    ),
                    InteractiveElement(
                        element_id="btn-download",
                        tag_name="button",
                        selector="#download-report",
                        text="Download CSV",
                    ),
                ],
            },
        }

        # Simulated failure flags for testing error paths
        self.fail_navigation = False
        self.fail_timeout = False
        self.fail_missing_element = False

    async def ainitialize(self) -> None:
        self.is_initialized = True
        self.is_closed = False

    async def anavigate(self, url: str, timeout_ms: Optional[int] = None) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            if not self.is_initialized or self.is_closed:
                await self.ainitialize()

            if self.fail_timeout:
                raise BrowserTimeoutError(f"Navigation to {url} timed out.", url=url)

            if self.fail_navigation:
                raise BrowserNavigationError(f"DNS lookup failed for host in {url}.", url=url)

            validated_url = self.security.validate_url(url)
            self.current_url = validated_url

            # Load page info if pre-configured, else generate default
            page_data = self.pages.get(validated_url, {
                "title": f"Page: {validated_url}",
                "text": f"Simulated content for {validated_url}",
                "elements": [
                    InteractiveElement(
                        element_id="btn-submit",
                        tag_name="button",
                        selector="#submit",
                        text="Submit",
                    )
                ],
            })
            self.current_title = page_data.get("title", "Page")
            self.scroll_pos = {"x": 0, "y": 0}

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
        except BrowserAdapterError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=err.recoverable,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )
        except Exception as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=str(err),
                error_code="UNEXPECTED_ERROR",
                error_category="runtime",
                recoverable=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    async def aobserve(self) -> BrowserObservation:
        page_data = self.pages.get(self.current_url, {
            "title": self.current_title,
            "text": f"Content of {self.current_url}",
            "elements": [],
        })

        elements = list(page_data.get("elements", []))

        return BrowserObservation(
            url=self.current_url,
            title=self.current_title,
            text_content=self.security.sanitize_text(page_data.get("text", "")),
            interactive_elements=elements,
            forms=[{"id": "simulated-form", "inputs": list(self.form_inputs.keys())}],
            scroll_position=dict(self.scroll_pos),
            status_code=200,
        )

    async def aclick(self, selector: str, timeout_ms: Optional[int] = None) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            if self.fail_timeout:
                raise BrowserTimeoutError(f"Click timed out waiting for element '{selector}'.", selector=selector)

            if self.fail_missing_element:
                raise BrowserElementNotFoundError(f"Element with selector '{selector}' not found.", selector=selector)

            obs = await self.aobserve()
            matching = [el for el in obs.interactive_elements if el.selector == selector]
            if not matching and selector not in {"#more-info", "#submit", "#download-report", "button", "a"}:
                raise BrowserElementNotFoundError(f"Element '{selector}' was not found on page.", selector=selector)

            self.clicked_elements.append(selector)
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"clicked": selector},
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserAdapterError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=err.recoverable,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    async def atype_text(
        self,
        selector: str,
        text: str,
        clear_existing: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            if self.fail_timeout:
                raise BrowserTimeoutError(f"Typing timed out on element '{selector}'.", selector=selector)

            if self.fail_missing_element:
                raise BrowserElementNotFoundError(f"Element '{selector}' not found for typing.", selector=selector)

            sanitized_input = self.security.sanitize_text(text)
            self.form_inputs[selector] = text  # store raw internally, redact in output

            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"selector": selector, "typed_length": len(text), "preview": sanitized_input},
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserAdapterError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=err.recoverable,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    async def aselect_option(
        self,
        selector: str,
        value: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            if self.fail_missing_element:
                raise BrowserElementNotFoundError(f"Select element '{selector}' not found.", selector=selector)

            self.form_inputs[selector] = value
            obs = await self.aobserve()
            latency = (time.perf_counter() - start) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                data={"selector": selector, "selected_value": value},
                observation=obs,
                latency_ms=round(latency, 2),
            )
        except BrowserAdapterError as err:
            return ActionResult(
                action_id=action_id,
                success=False,
                error=err.message,
                error_code=err.code,
                error_category=err.category,
                recoverable=err.recoverable,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    async def ascroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())
        step = amount if amount is not None else 500

        if direction == "down":
            self.scroll_pos["y"] += step
        elif direction == "up":
            self.scroll_pos["y"] = max(0, self.scroll_pos["y"] - step)
        elif direction == "top":
            self.scroll_pos["y"] = 0
        elif direction == "bottom":
            self.scroll_pos["y"] = 2500

        obs = await self.aobserve()
        latency = (time.perf_counter() - start) * 1000

        return ActionResult(
            action_id=action_id,
            success=True,
            data={"scroll_position": dict(self.scroll_pos), "direction": direction},
            observation=obs,
            latency_ms=round(latency, 2),
        )

    async def aextract_content(
        self,
        selector: Optional[str] = None,
        extract_type: str = "text",
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        obs = await self.aobserve()
        content: Any = obs.text_content

        if selector:
            content = f"Extracted {extract_type} from {selector}"

        latency = (time.perf_counter() - start) * 1000
        return ActionResult(
            action_id=action_id,
            success=True,
            data={"extracted_type": extract_type, "content": content},
            observation=obs,
            latency_ms=round(latency, 2),
        )

    async def aupload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            # Security verification
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

    async def adownload_file(
        self,
        trigger_selector: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        start = time.perf_counter()
        action_id = str(uuid.uuid4())

        try:
            # Validate target download path
            filename = "report_export.csv" if not save_path else None
            safe_dest = self.security.validate_download_path(save_path, filename=filename)

            # In mock mode, create simulated file at safe destination
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

    async def aclose(self) -> None:
        self.is_closed = True
        self.is_initialized = False
 main


__all__ = ["MockBrowserAdapter"]
