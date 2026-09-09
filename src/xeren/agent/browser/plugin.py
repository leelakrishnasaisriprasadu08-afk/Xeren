"""BrowserPlugin adapting BaseBrowserAdapter to Xeren's standard BasePlugin contract."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel, Field

from xeren.agent.browser.adapter import (
    BaseBrowserAdapter,
    BrowserActionType,
    BrowserObservation,
)
from xeren.agent.browser.mock import MockBrowserAdapter
from xeren.plugins.contract import (
    BasePlugin,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)

logger = logging.getLogger("xeren.agent.browser.plugin")


class BrowserInput(BaseModel):
    """Input schema for generic browser plugin operations."""

    action: str = Field(
        ...,
        description="Browser action: navigate, observe, click, type, select, scroll, extract, upload, download, close",
    )
    url: Optional[str] = Field(
        default=None,
        description="Target URL for navigation or download",
    )
    selector: Optional[str] = Field(
        default=None,
        description="Element selector for interaction or extraction",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text content to type",
    )
    value: Optional[str] = Field(
        default=None,
        description="Dropdown option value",
    )
    direction: str = Field(
        default="down",
        description="Scroll direction ('up' or 'down')",
    )
    amount: int = Field(
        default=500,
        description="Scroll distance in pixels",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="File path for upload operations",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional options",
    )

    model_config = {"arbitrary_types_allowed": True}


class BrowserResult(BaseModel):
    """Output schema for generic browser plugin executions."""

    action: str = Field(
        ...,
        description="The browser action that was executed",
    )
    success: bool = Field(
        ...,
        description="Whether the browser operation succeeded",
    )
    observation: Optional[BrowserObservation] = Field(
        default=None,
        description="Observed browser state after operation",
    )
    data: Optional[Any] = Field(
        default=None,
        description="Extracted or downloaded data",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error detail if operation failed",
    )

    model_config = {"arbitrary_types_allowed": True}


class BrowserPlugin(BasePlugin):
    """Modular browser automation plugin integrating BaseBrowserAdapter with PluginManager."""

    def __init__(self, adapter: Optional[BaseBrowserAdapter] = None) -> None:
        self.adapter = adapter or MockBrowserAdapter()

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="browser",
            version="0.1.0",
            description="Generic Web Browser automation plugin for Xeren Autonomous Agent",
            capabilities=["browser_automation", "web_interaction"],
            input_schema_name="BrowserInput",
            output_schema_name="BrowserResult",
            author="Xeren",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return BrowserInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return BrowserResult

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Execute a browser action using the configured browser adapter."""
        start_time = time.perf_counter()
        validated: BrowserInput = (
            input_data if isinstance(input_data, BrowserInput) else self.validate_input(input_data)  # type: ignore
        )

        action_name = validated.action.lower().strip()
        logger.debug("Executing BrowserPlugin action: %s", action_name)

        try:
            obs: Optional[BrowserObservation] = None
            data: Optional[Any] = None

            if action_name == BrowserActionType.NAVIGATE.value:
                if not validated.url:
                    raise ValueError("Action 'navigate' requires a 'url' parameter.")
                obs = self.adapter.navigate(validated.url)
            elif action_name == BrowserActionType.OBSERVE.value:
                obs = self.adapter.observe()
            elif action_name == BrowserActionType.CLICK.value:
                if not validated.selector:
                    raise ValueError("Action 'click' requires a 'selector' parameter.")
                obs = self.adapter.click(validated.selector)
            elif action_name == BrowserActionType.TYPE.value:
                if not validated.selector or validated.text is None:
                    raise ValueError("Action 'type' requires both 'selector' and 'text' parameters.")
                obs = self.adapter.type(validated.selector, validated.text)
            elif action_name == BrowserActionType.SELECT.value:
                if not validated.selector or validated.value is None:
                    raise ValueError("Action 'select' requires both 'selector' and 'value' parameters.")
                obs = self.adapter.select(validated.selector, validated.value)
            elif action_name == BrowserActionType.SCROLL.value:
                obs = self.adapter.scroll(direction=validated.direction, amount=validated.amount)
            elif action_name == BrowserActionType.EXTRACT.value:
                data = self.adapter.extract(selector=validated.selector)
                obs = self.adapter.observe()
            elif action_name == BrowserActionType.UPLOAD.value:
                if not validated.selector or not validated.file_path:
                    raise ValueError("Action 'upload' requires 'selector' and 'file_path'.")
                obs = self.adapter.upload(validated.selector, validated.file_path)
            elif action_name == BrowserActionType.DOWNLOAD.value:
                raw_bytes = self.adapter.download(url=validated.url, selector=validated.selector)
                data = raw_bytes.decode("utf-8", errors="replace")
                obs = self.adapter.observe()
            elif action_name == BrowserActionType.CLOSE.value:
                self.adapter.close()
            else:
                raise ValueError(f"Unsupported browser action '{action_name}'.")

            result = BrowserResult(
                action=action_name,
                success=True,
                observation=obs,
                data=data,
            )

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
                metadata={"action": action_name},
            )

        except Exception as err:
            logger.exception("BrowserPlugin execution failed for '%s': %s", action_name, err)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result = BrowserResult(
                action=action_name,
                success=False,
                error=str(err),
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=False,
                output=result,
                error=str(err),
                latency_ms=latency_ms,
            )

    def shutdown(self) -> None:
        """Release browser resources on plugin shutdown."""
        try:
            self.adapter.close()
        except Exception as err:
            logger.warning("Error closing browser adapter during shutdown: %s", err)


__all__ = [
    "BrowserInput",
    "BrowserResult",
    "BrowserPlugin",
]
