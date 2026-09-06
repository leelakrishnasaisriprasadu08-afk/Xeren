"""Structured exception hierarchy for browser automation and adapter operations."""

from typing import Any, Dict, Optional
from xeren.agent.types import BrowserError


class BrowserAdapterError(Exception):
    """Base exception for all browser adapter failures."""

    def __init__(
        self,
        message: str,
        code: str = "BROWSER_ERROR",
        category: str = "general",
        selector: Optional[str] = None,
        url: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.selector = selector
        self.url = url
        self.recoverable = recoverable
        self.details = details or {}

    def to_browser_error(self) -> BrowserError:
        """Convert exception to a structured, serializable BrowserError model."""
        return BrowserError(
            code=self.code,
            message=self.message,
            category=self.category,
            selector=self.selector,
            url=self.url,
            recoverable=self.recoverable,
            details=self.details,
        )


class BrowserNavigationError(BrowserAdapterError):
    """Raised when navigation to a URL fails (DNS, connection reset, 4xx/5xx)."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="NAVIGATION_FAILED",
            category="network",
            url=url,
            recoverable=recoverable,
            details=details,
        )


class BrowserTimeoutError(BrowserAdapterError):
    """Raised when a navigation or element interaction times out."""

    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        url: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TIMEOUT",
            category="timeout",
            selector=selector,
            url=url,
            recoverable=recoverable,
            details=details,
        )


class BrowserElementNotFoundError(BrowserAdapterError):
    """Raised when an expected DOM element or selector cannot be located."""

    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        url: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="ELEMENT_NOT_FOUND",
            category="dom",
            selector=selector,
            url=url,
            recoverable=recoverable,
            details=details,
        )


class BrowserSecurityError(BrowserAdapterError):
    """Raised when a security boundary is violated (path traversal, unauthorized schemes, secret leak)."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="SECURITY_VIOLATION",
            category="security",
            url=url,
            recoverable=False,  # Security violations are non-recoverable
            details=details,
        )


class BrowserSessionError(BrowserAdapterError):
    """Raised when the browser instance crashes, fails to launch, or is closed prematurely."""

    def __init__(
        self,
        message: str,
        recoverable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="SESSION_ERROR",
            category="runtime",
            recoverable=recoverable,
            details=details,
        )


class BrowserActionError(BrowserAdapterError):
    """Raised when a specific browser action (e.g. click, scroll, select) fails."""

    def __init__(
        self,
        message: str,
        action: str,
        selector: Optional[str] = None,
        url: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        det = details or {}
        det["action"] = action
        super().__init__(
            message=message,
            code=f"{action.upper()}_FAILED",
            category="action",
            selector=selector,
            url=url,
            recoverable=recoverable,
            details=det,
        )
