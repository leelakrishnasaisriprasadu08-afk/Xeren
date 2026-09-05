"""Tool registry aggregating website creation, analysis, validation, security, and preview tools."""

from typing import Optional

from xeren.models.base import BaseLLM
from xeren.models.providers.mock import MockLLM
from xeren.plugins.coding.plugin import CodingPlugin
from xeren.plugins.website.tools.generator import WebsiteGeneratorTool
from xeren.plugins.website.tools.preview import BasePreviewProvider, MockPreviewProvider
from xeren.plugins.website.tools.requirements import RequirementAnalysisTool
from xeren.plugins.website.tools.security import WebsiteSecurityTool
from xeren.plugins.website.tools.validator import WebsiteValidatorTool


class WebsiteToolRegistry:
    """Coordinates modular tools for website requirements, generation, validation, and security."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        coding_plugin: Optional[CodingPlugin] = None,
        requirements_tool: Optional[RequirementAnalysisTool] = None,
        generator_tool: Optional[WebsiteGeneratorTool] = None,
        validator_tool: Optional[WebsiteValidatorTool] = None,
        security_tool: Optional[WebsiteSecurityTool] = None,
        preview_provider: Optional[BasePreviewProvider] = None,
    ) -> None:
        self.llm = llm or MockLLM()
        self.coding_plugin = coding_plugin or CodingPlugin(llm=self.llm)

        self.requirements_tool = requirements_tool or RequirementAnalysisTool(llm=self.llm)
        self.generator_tool = generator_tool or WebsiteGeneratorTool(
            coding_plugin=self.coding_plugin,
            generation_tool=self.coding_plugin.registry.generation_tool,
        )
        self.validator_tool = validator_tool or WebsiteValidatorTool(
            syntax_tool=self.coding_plugin.registry.syntax_tool
        )
        self.security_tool = security_tool or WebsiteSecurityTool()
        self.preview_provider = preview_provider or MockPreviewProvider()

    def set_llm(self, llm: BaseLLM) -> None:
        """Update active LLM provider across registered tools."""
        self.llm = llm
        self.requirements_tool.set_llm(llm)
        if self.coding_plugin:
            self.coding_plugin.set_llm(llm)

    def set_coding_plugin(self, plugin: CodingPlugin) -> None:
        """Update the underlying CodingPlugin instance."""
        self.coding_plugin = plugin
        self.generator_tool.coding_plugin = plugin
        self.generator_tool.generation_tool = plugin.registry.generation_tool
        self.validator_tool.syntax_tool = plugin.registry.syntax_tool

    def set_preview_provider(self, provider: BasePreviewProvider) -> None:
        """Update the active preview provider."""
        self.preview_provider = provider


__all__ = ["WebsiteToolRegistry"]
