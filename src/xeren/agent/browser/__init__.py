"""Generic browser abstraction package for Xeren Autonomous Work Agent."""

from xeren.agent.browser.adapter import (
    BaseBrowserAdapter,
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

__all__ = [
    "BaseBrowserAdapter",
    "BrowserActionType",
    "BrowserAction",
    "BrowserObservation",
    "MockBrowserAdapter",
    "BrowserInput",
    "BrowserResult",
    "BrowserPlugin",
]
