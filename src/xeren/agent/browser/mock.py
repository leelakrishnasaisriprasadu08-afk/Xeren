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
                "elements": [],
            },
            "https://example.com": {
                "title": "Example Domain",
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

    def extract(self, selector: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
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

    def upload(self, selector: str, file_path: str, **kwargs: Any) -> BrowserObservation:
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


__all__ = ["MockBrowserAdapter"]
