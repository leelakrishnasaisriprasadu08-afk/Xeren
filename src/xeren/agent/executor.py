"""Executor responsible for action dispatch, tool execution, and permission validation."""

import asyncio
import logging
import time
from typing import Any, Optional

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.permissions import PermissionManager
from xeren.agent.types import ActionResult, AgentAction, BrowserObservation
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.executor")


class Executor:
    """Dispatches AgentAction instances to browser adapters or plugin subsystems with permission enforcement."""

    def __init__(
        self,
        browser_adapter: BaseBrowserAdapter,
        permission_manager: Optional[PermissionManager] = None,
        plugin_manager: Optional[PluginManager] = None,
    ) -> None:
        self.browser = browser_adapter
        self.permissions = permission_manager or PermissionManager()
        self.plugins = plugin_manager

    def set_browser_adapter(self, adapter: BaseBrowserAdapter) -> None:
        """Switch or update the active browser adapter (e.g. Mock -> Real)."""
        self.browser = adapter

    async def aexecute(self, action: AgentAction) -> ActionResult:
        """Asynchronously dispatch and execute an AgentAction."""
        start = time.perf_counter()

        # 1. Enforce permission policies
        allowed, denial_reason = self.permissions.check_permission(action)
        if not allowed:
            logger.warning("Action %s blocked by permission manager: %s", action.action_id, denial_reason)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=denial_reason or "Permission denied",
                error_code="PERMISSION_DENIED",
                error_category="security",
                recoverable=False,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        action_type = action.action_type.lower()

        # 2. Dispatch to PluginManager if action targets a plugin
        target_plugin = action.parameters.get("plugin_name") if action_type == "plugin" else (
            action_type if (self.plugins and self.plugins.has(action_type)) else None
        )
        if action_type == "plugin" and not target_plugin:
            target_plugin = action.target

        if target_plugin or action_type == "plugin":
            if not self.plugins or not target_plugin or not self.plugins.has(target_plugin):
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error=f"Plugin '{target_plugin}' is not registered or supported.",
                    error_code="UNSUPPORTED_PLUGIN",
                    error_category="plugin",
                    recoverable=False,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )

            try:
                plugin_payload = action.parameters.get("input")
                if plugin_payload is None:
                    plugin_payload = {
                        k: v for k, v in action.parameters.items() if k not in {"plugin_name", "capability"}
                    }
                if action.target and "query" not in plugin_payload and target_plugin == "research":
                    plugin_payload["query"] = action.target

                plugin_res = await self.plugins.aexecute(target_plugin, plugin_payload)
                output_dict: Any = None
                if plugin_res.output is not None:
                    output_dict = (
                        plugin_res.output.model_dump()
                        if hasattr(plugin_res.output, "model_dump")
                        else plugin_res.output
                    )

                return ActionResult(
                    action_id=action.action_id,
                    success=plugin_res.success,
                    data=output_dict if isinstance(output_dict, dict) else ({"result": output_dict} if output_dict is not None else {}),
                    error=plugin_res.error,
                    error_code=None if plugin_res.success else "PLUGIN_ERROR",
                    error_category=None if plugin_res.success else "plugin",
                    recoverable=not plugin_res.success,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    metadata={"plugin_name": target_plugin, **plugin_res.metadata},
                )
            except Exception as err:
                logger.exception("Exception executing plugin '%s': %s", target_plugin, err)
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error=str(err),
                    error_code="PLUGIN_EXECUTION_ERROR",
                    error_category="plugin",
                    recoverable=False,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )

        # 3. Dispatch to Browser Adapter
        try:
            if action_type == "navigate":
                url = action.target or action.parameters.get("url", "about:blank")
                return await self.browser.anavigate(url, timeout_ms=action.parameters.get("timeout_ms"))

            elif action_type == "observe":
                obs = await self.browser.aobserve()
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    data={"url": obs.url, "title": obs.title},
                    observation=obs,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )

            elif action_type == "click":
                selector = action.target or action.parameters.get("selector", "")
                return await self.browser.aclick(selector, timeout_ms=action.parameters.get("timeout_ms"))

            elif action_type == "type":
                selector = action.target or action.parameters.get("selector", "")
                text = action.parameters.get("text", "")
                clear = action.parameters.get("clear_existing", True)
                return await self.browser.atype_text(selector, text, clear_existing=clear)

            elif action_type == "select":
                selector = action.target or action.parameters.get("selector", "")
                value = action.parameters.get("value", "")
                return await self.browser.aselect_option(selector, value)

            elif action_type == "scroll":
                direction = action.parameters.get("direction", "down")
                amount = action.parameters.get("amount")
                return await self.browser.ascroll(direction=direction, amount=amount)

            elif action_type == "extract":
                selector = action.target or action.parameters.get("selector")
                extract_type = action.parameters.get("extract_type", "text")
                return await self.browser.aextract_content(selector=selector, extract_type=extract_type)

            elif action_type == "upload":
                selector = action.target or action.parameters.get("selector", "input[type='file']")
                file_path = action.parameters.get("file_path", "")
                return await self.browser.aupload_file(selector=selector, file_path=file_path)

            elif action_type == "download":
                trigger_selector = action.parameters.get("trigger_selector") or action.target
                save_path = action.parameters.get("save_path")
                return await self.browser.adownload_file(trigger_selector=trigger_selector, save_path=save_path)

            elif action_type == "close":
                await self.browser.aclose()
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    data={"closed": True},
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )

            else:
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error=f"Unrecognized action type: '{action_type}'",
                    error_code="INVALID_ACTION",
                    error_category="validation",
                    recoverable=False,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )

        except Exception as err:
            logger.exception("Exception during action execution (%s): %s", action_type, err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(err),
                error_code="EXECUTION_ERROR",
                error_category="runtime",
                recoverable=True,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    def execute(self, action: AgentAction) -> ActionResult:
        """Synchronous wrapper for action execution."""
        return asyncio.run(self.aexecute(action))


__all__ = ["Executor"]
