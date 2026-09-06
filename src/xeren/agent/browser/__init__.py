"""Browser adapter package exposing base contracts, mock implementations, and Playwright adapter."""

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.errors import (
    BrowserActionError,
    BrowserAdapterError,
    BrowserElementNotFoundError,
    BrowserNavigationError,
    BrowserSecurityError,
    BrowserSessionError,
    BrowserTimeoutError,
)
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.browser.playwright_adapter import PlaywrightBrowserAdapter
from xeren.agent.browser.security import BrowserSecurityManager

__all__ = [
    "BaseBrowserAdapter",
    "MockBrowserAdapter",
    "PlaywrightBrowserAdapter",
    "BrowserSecurityManager",
    "BrowserAdapterError",
    "BrowserNavigationError",
    "BrowserTimeoutError",
    "BrowserElementNotFoundError",
    "BrowserSecurityError",
    "BrowserSessionError",
    "BrowserActionError",
]
