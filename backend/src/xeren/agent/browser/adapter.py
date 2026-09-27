"""Generic browser abstraction, action schemas, and adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BrowserActionType(str, Enum):
    """Primitve operations supported by the generic browser abstraction."""

    NAVIGATE = "navigate"
    OBSERVE = "observe"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    EXTRACT = "extract"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    CLOSE = "close"


class BrowserAction(BaseModel):
    """Specification of a generic browser operation."""

    action_type: BrowserActionType = Field(
        ...,
        description="Browser primitive operation to perform",
    )
    url: Optional[str] = Field(
        default=None,
        description="Target URL for navigation or download",
    )
    selector: Optional[str] = Field(
        default=None,
        description="Generic target selector (CSS/XPath/semantic identifier)",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text content to type into an input field",
    )
    value: Optional[str] = Field(
        default=None,
        description="Option value for dropdown selection",
    )
    direction: str = Field(
        default="down",
        description="Scroll direction ('up' or 'down')",
    )
    amount: int = Field(
        default=500,
        ge=0,
        description="Scroll amount in pixels",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Local file path for upload operations",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional browser execution options",
    )

    model_config = {"arbitrary_types_allowed": True}


class BrowserObservation(BaseModel):
    """Perception of the current browser page state."""

    url: str = Field(
        ...,
        description="Current page URL",
    )
    title: str = Field(
        default="",
        description="Current page title",
    )
    content: str = Field(
        default="",
        description="Extracted text or DOM content",
    )
    status_code: int = Field(
        default=200,
        description="HTTP status code of the page",
    )
    elements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Interactive or queryable elements visible on the page",
    )
    screenshot: Optional[str] = Field(
        default=None,
        description="Base64 or file path reference to page screenshot if captured",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Browser runtime metadata",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def success(self) -> bool:
        """Indicate observation succeeded."""
        err = getattr(self, "error", None)
        status = getattr(self, "status_code", 200)
        return err is None and (status is None or status < 400)


class BaseBrowserAdapter(ABC):
    """Abstract contract for generic web browser automation.

    Decouples the agent from concrete browser automation tools (Playwright, Puppeteer,
    Selenium, or MockBrowserAdapter).
    """

    @abstractmethod
    def navigate(self, url: str) -> BrowserObservation:
        """Navigate to a URL and return the resulting page observation."""
        pass

    @abstractmethod
    def observe(self) -> BrowserObservation:
        """Observe the current page state without mutating it."""
        pass

    @abstractmethod
    def click(self, selector: str) -> BrowserObservation:
        """Click an element identified by selector."""
        pass

    @abstractmethod
    def type(self, selector: str, text: str) -> BrowserObservation:
        """Type text into an input field identified by selector."""
        pass

    @abstractmethod
    def select(self, selector: str, value: str) -> BrowserObservation:
        """Select an option from a dropdown element."""
        pass

    @abstractmethod
    def scroll(self, direction: str = "down", amount: int = 500) -> BrowserObservation:
        """Scroll the current page viewport."""
        pass

    @abstractmethod
    def extract(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured data or text content matching the selector."""
        pass

    @abstractmethod
    def upload(self, selector: str, file_path: str) -> BrowserObservation:
        """Upload a file to an input element."""
        pass

    @abstractmethod
    def download(self, url: Optional[str] = None, selector: Optional[str] = None) -> bytes:
        """Download binary content from a URL or by clicking a selector."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close browser context and release resources."""
        pass

    def initialize(self) -> None:
        """Initialize browser session if needed."""
        pass

    # Async convenience methods
    async def ainitialize(self) -> None:
        """Asynchronously initialize browser session."""
        await asyncio.to_thread(self.initialize)

    async def anavigate(self, url: str) -> BrowserObservation:
        return await asyncio.to_thread(self.navigate, url)

    async def aobserve(self) -> BrowserObservation:
        return await asyncio.to_thread(self.observe)

    async def aclick(self, selector: str) -> BrowserObservation:
        return await asyncio.to_thread(self.click, selector)

    async def atype(self, selector: str, text: str) -> BrowserObservation:
        return await asyncio.to_thread(self.type, selector, text)

    async def aselect(self, selector: str, value: str) -> BrowserObservation:
        return await asyncio.to_thread(self.select, selector, value)

    async def ascroll(self, direction: str = "down", amount: int = 500) -> BrowserObservation:
        return await asyncio.to_thread(self.scroll, direction, amount)

    async def aextract(self, selector: Optional[str] = None) -> Dict[str, Any]:
        return await asyncio.to_thread(self.extract, selector)

    async def aupload(self, selector: str, file_path: str) -> BrowserObservation:
        return await asyncio.to_thread(self.upload, selector, file_path)

    async def adownload(self, url: Optional[str] = None, selector: Optional[str] = None) -> bytes:
        return await asyncio.to_thread(self.download, url, selector)

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)


__all__ = [
    "BrowserActionType",
    "BrowserAction",
    "BrowserObservation",
    "BaseBrowserAdapter",
]
