"""Xeren AI Framework Package."""

from xeren.agent import (
    Action,
    ActionResult,
    AgentController,
    MockPlanner,
    TaskState,
    TaskStatus,
)
from xeren.core.runtime import XerenCore
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.contract import BasePlugin
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.manager import PluginManager
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.website.plugin import WebsitePlugin

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "XerenCore",
    "PluginManager",
    "BasePlugin",
    "ResearchPlugin",
    "KnowledgePlugin",
    "CodingPlugin",
    "WebsitePlugin",
    "DataPlugin",
    "AgentController",
    "TaskState",
    "TaskStatus",
    "Action",
    "ActionResult",
    "MockPlanner",
]
