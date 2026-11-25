"""Abstract base contract for browser adapters in Xeren."""

from abc import ABC, abstractmethod
import asyncio
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union

from xeren.agent.types import ActionResult, BrowserObservation


class BaseBrowserAdapter(ABC):
    """Abstract interface defining required browser automation capabilities."""

    @abstractmethod
    async def ainitialize(self) -> None:
        """Asynchronously initialize the browser session."""
        pass

    def initialize(self) -> None:
        """Synchronously initialize the browser session."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Scheduled in active event loop
                asyncio.create_task(self.ainitialize())
                return
            loop.run_until_complete(self.ainitialize())
        except RuntimeError:
            asyncio.run(self.ainitialize())

    @abstractmethod
    async def anavigate(self, url: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Navigate to a target URL."""
        pass

    def navigate(self, url: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Synchronous wrapper for navigation."""
        return asyncio.run(self.anavigate(url, timeout_ms))

    @abstractmethod
    async def aobserve(self) -> BrowserObservation:
        """Extract structured observation from the currently active page."""
        pass

    def observe(self) -> BrowserObservation:
        """Synchronous wrapper for page observation."""
        return asyncio.run(self.aobserve())

    @abstractmethod
    async def aclick(self, selector: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Click an element matching the given selector."""
        pass

    def click(self, selector: str, timeout_ms: Optional[int] = None) -> ActionResult:
        """Synchronous wrapper for element click."""
        return asyncio.run(self.aclick(selector, timeout_ms))

    @abstractmethod
    async def atype_text(
        self,
        selector: str,
        text: str,
        clear_existing: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Enter text into an input or textarea element."""
        pass

    def type_text(
        self,
        selector: str,
        text: str,
        clear_existing: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Synchronous wrapper for text input."""
        return asyncio.run(self.atype_text(selector, text, clear_existing, timeout_ms))

    @abstractmethod
    async def aselect_option(
        self,
        selector: str,
        value: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Select an option in a dropdown element by value or label."""
        pass

    def select_option(
        self,
        selector: str,
        value: str,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Synchronous wrapper for select option."""
        return asyncio.run(self.aselect_option(selector, value, timeout_ms))

    @abstractmethod
    async def ascroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> ActionResult:
        """Scroll the page in the specified direction ('up', 'down', 'top', 'bottom')."""
        pass

    def scroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> ActionResult:
        """Synchronous wrapper for scrolling."""
        return asyncio.run(self.ascroll(direction, amount))

    @abstractmethod
    async def aextract_content(
        self,
        selector: Optional[str] = None,
        extract_type: str = "text",
    ) -> ActionResult:
        """Extract structured content ('text', 'html', 'table', 'attribute') from the page."""
        pass

    def extract_content(
        self,
        selector: Optional[str] = None,
        extract_type: str = "text",
    ) -> ActionResult:
        """Synchronous wrapper for content extraction."""
        return asyncio.run(self.aextract_content(selector, extract_type))

    @abstractmethod
    async def aupload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        """Upload a file to an input[type=file] element through controlled paths."""
        pass

    def upload_file(
        self,
        selector: str,
        file_path: Union[str, Path],
    ) -> ActionResult:
        """Synchronous wrapper for file upload."""
        return asyncio.run(self.aupload_file(selector, file_path))

    @abstractmethod
    async def adownload_file(
        self,
        trigger_selector: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Trigger and safely download a file to an approved workspace path."""
        pass

    def download_file(
        self,
        trigger_selector: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ActionResult:
        """Synchronous wrapper for file download."""
        return asyncio.run(self.adownload_file(trigger_selector, save_path, timeout_ms))

    @abstractmethod
    async def aclose(self) -> None:
        """Asynchronously close the browser session and clean up all resources."""
        pass

    def close(self) -> None:
        """Synchronously close the browser session and clean up all resources."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.aclose())
                return
            loop.run_until_complete(self.aclose())
        except RuntimeError:
            asyncio.run(self.aclose())

    async def __aenter__(self) -> "BaseBrowserAdapter":
        await self.ainitialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()


__all__ = ["BaseBrowserAdapter"]
