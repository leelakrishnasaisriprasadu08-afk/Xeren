"""Xeren Modular Plugin System.

Exports all official plugins, contracts, errors, and manager factories.
"""

from typing import Optional

from xeren.models.base import BaseLLM
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginCapability,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.errors import (
    PluginError,
    PluginExecutionError,
    PluginHealthCheckError,
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)
from xeren.plugins.manager import PluginManager

# Modular Plugins
from xeren.plugins.api.plugin import ApiPlugin
from xeren.plugins.automation.plugin import AutomationPlugin
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.conversation.plugin import ConversationPlugin
from xeren.plugins.data.plugin import DataPlugin
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.file.plugin import FilePlugin
from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.plugins.research.plugin import ResearchPlugin
from xeren.plugins.research.tools.search import BaseSearchEngine
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.website.plugin import WebsitePlugin


def create_default_plugin_manager(
    llm: Optional[BaseLLM] = None,
    search_engine: Optional[BaseSearchEngine] = None,
) -> PluginManager:
    """Convenience factory to instantiate a PluginManager loaded with all core plugins."""
    manager = PluginManager()

    # 1. Research & Knowledge
    research = ResearchPlugin(llm=llm, search_engine=search_engine)
    manager.register(research)

    knowledge = KnowledgePlugin()
    manager.register(knowledge)

    # 2. Coding & Website (User Idea Architecture)
    coding = CodingPlugin(llm=llm)
    manager.register(coding)

    website = WebsitePlugin(llm=llm, coding_plugin=coding)
    manager.register(website)

    # 3. Data & File
    data = DataPlugin()
    manager.register(data)

    file_p = FilePlugin()
    manager.register(file_p)

    # 4. Verification & Experience
    verification = VerificationPlugin()
    manager.register(verification)

    experience = ExperiencePlugin()
    manager.register(experience)

    # 5. Automation & API
    automation = AutomationPlugin(plugin_manager=manager)
    manager.register(automation)

    api = ApiPlugin(plugin_manager=manager)
    manager.register(api)

    # 6. Conversation
    conversation = ConversationPlugin(llm=llm)
    manager.register(conversation)

    return manager


__all__ = [
    # Core contracts
    "BasePlugin",
    "PluginCapability",
    "PluginHealthStatus",
    "HealthCheckResult",
    "PluginManifest",
    "PluginExecutionContext",
    "PluginExecutionResult",
    "PluginManager",
    "create_default_plugin_manager",
    # Plugins
    "ApiPlugin",
    "AutomationPlugin",
    "CodingPlugin",
    "ConversationPlugin",
    "DataPlugin",
    "ExperiencePlugin",
    "FilePlugin",
    "KnowledgePlugin",
    "ResearchPlugin",
    "VerificationPlugin",
    "WebsitePlugin",
    # Errors
    "PluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "PluginExecutionError",
    "PluginTimeoutError",
    "PluginHealthCheckError",
]
