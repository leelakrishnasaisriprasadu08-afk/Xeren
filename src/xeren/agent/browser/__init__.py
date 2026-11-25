"""Generic browser abstraction package for Xeren Autonomous Work Agent."""

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.browser.adapter import (
    BrowserAction,
    BrowserActionType,
    BrowserObservation,
)
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.agent.browser.plugin import (
    BrowserInput,
    BrowserPlugin,
    BrowserResult,
)
from xeren.agent.browser.errors import (
    BrowserActionError,
    BrowserAdapterError,
    BrowserElementNotFoundError,
    BrowserNavigationError,
    BrowserSecurityError,
    BrowserSessionError,
    BrowserTimeoutError,
)
from xeren.agent.browser.playwright_adapter import PlaywrightBrowserAdapter
from xeren.agent.browser.security import BrowserSecurityManager

__all__ = [
    "BaseBrowserAdapter",
    "BrowserActionType",
    "BrowserAction",
    "BrowserObservation",
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
    "BrowserInput",
    "BrowserResult",
    "BrowserPlugin",
]
