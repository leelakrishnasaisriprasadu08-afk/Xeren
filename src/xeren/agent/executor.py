"""AgentExecutor executing actions strictly through the existing PluginManager."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import Executor as BaseExecutor
from xeren.plugins.contract import PluginExecutionContext, PluginExecutionResult
from xeren.plugins.errors import (
    PluginError,
    PluginExecutionError,
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)

import asyncio
import logging
import time
from typing import Any, Optional

from xeren.agent.browser.contract import BaseBrowserAdapter
from xeren.agent.permissions import PermissionManager
from xeren.agent.types import ActionResult, AgentAction, BrowserObservation
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.executor")

class AgentExecutor(BaseExecutor):
    """Executes actions strictly through the existing Xeren PluginManager.

    Provides plugin failure isolation, timeout handling, artifact extraction,
    and translation into standardized ActionResults.
    """

    def __init__(
        self,
        plugin_manager: PluginManager,
        workspace_manager: Optional[Any] = None,
        browser_adapter: Optional[Any] = None,
    ) -> None:
        self.plugin_manager = plugin_manager
        self.workspace_manager = workspace_manager
        self.browser_adapter = browser_adapter
        self.browser = browser_adapter

    def set_browser_adapter(self, adapter: Optional[Any]) -> None:
        """Set or update the active browser adapter."""
        self.browser_adapter = adapter
        self.browser = adapter

    def execute(
        self,
        action: Action,
        context: Optional[PluginExecutionContext] = None,
    ) -> ActionResult:
        """Synchronously execute an action via the PluginManager or WorkspaceManager."""
        start_time = time.perf_counter()
        target = action.target.lower()

        logger.debug("Executing action '%s' on target '%s'", action.action_id, target)

        # 1. Handle workspace actions directly via WorkspaceManager
        if target == "workspace":
            return self._execute_workspace(action, start_time)

        # 2. Handle desktop/os alias
        if target in ("desktop", "os") and self.plugin_manager.has("automation"):
            target = "automation"

        # 3. Handle browser adapter actions directly
        if target == "browser" and self.browser_adapter and not self.plugin_manager.has("browser"):
            return self._execute_browser(action, start_time)

        # 2. Verify target plugin exists
        if not self.plugin_manager.has(target):
            available = self.plugin_manager.list_names()
            msg = f"Target plugin '{target}' is not registered in PluginManager. Available: {available}"
            logger.warning(msg)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=msg,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": "PluginNotFoundError"},
            )

        # 2. Execute with failure isolation
        ctx = context or PluginExecutionContext(
            timeout_seconds=action.timeout_seconds,
            metadata=action.metadata,
        )

        try:
            plugin_res: PluginExecutionResult = self.plugin_manager.execute(
                name=target,
                input_data=action.parameters,
                context=ctx,
                timeout=action.timeout_seconds,
                raise_on_error=False,
            )

            latency_ms = (
                plugin_res.latency_ms
                if plugin_res.latency_ms > 0
                else round((time.perf_counter() - start_time) * 1000, 2)
            )

            # 3. Extract artifacts from output
            artifacts = self._extract_artifacts(plugin_res.output)

            return ActionResult(
                action_id=action.action_id,
                success=plugin_res.success,
                output=plugin_res.output,
                error=plugin_res.error,
                latency_ms=latency_ms,
                artifacts=artifacts,
                metadata={
                    "plugin_name": plugin_res.plugin_name,
                    "target": target,
                    **plugin_res.metadata,
                },
            )

        except PluginTimeoutError as err:
            logger.warning("Plugin '%s' execution timed out: %s", target, err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=f"Plugin execution timed out: {err.message}",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": "PluginTimeoutError"},
            )
        except (PluginValidationError, PluginExecutionError, PluginError) as err:
            logger.warning("Plugin '%s' execution error: %s", target, err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": err.__class__.__name__},
            )
        except Exception as err:
            logger.exception("Unexpected error executing action on '%s': %s", target, err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=f"Unexpected execution failure: {err}",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": "UnexpectedException"},
            )

    async def aexecute(
        self,
        action: Action,
        context: Optional[PluginExecutionContext] = None,
    ) -> ActionResult:
        """Asynchronously execute an action via the PluginManager."""
        start_time = time.perf_counter()
        raw_target = getattr(action, "target", None)
        action_type = getattr(action, "action_type", "")
        if hasattr(action_type, "value"):
            action_type = action_type.value

        if raw_target:
            target = str(raw_target).lower()
        elif action_type:
            type_lower = str(action_type).lower()
            if "code" in type_lower:
                target = "coding"
            elif "research" in type_lower or "search" in type_lower:
                target = "research"
            elif "data" in type_lower:
                target = "data"
            elif "web" in type_lower or "site" in type_lower:
                target = "website"
            elif "file" in type_lower:
                target = "file"
            elif "freelance" in type_lower or "auto" in type_lower:
                target = "automation"
            else:
                target = type_lower
        else:
            target = "system"

        logger.debug("Async executing action '%s' on target '%s'", action.action_id, target)

        if target == "workspace":
            return self._execute_workspace(action, start_time)

        # Handle desktop/os alias
        if target in ("desktop", "os") and self.plugin_manager.has("automation"):
            target = "automation"

        # Handle browser adapter actions directly
        if target == "browser" and self.browser_adapter and not self.plugin_manager.has("browser"):
            return await self._aexecute_browser(action, start_time)

        if not self.plugin_manager.has(target):
            available = self.plugin_manager.list_names()
            msg = f"Target plugin '{target}' is not registered in PluginManager. Available: {available}"
            action_id = getattr(action, "action_id", "act_0")
            return ActionResult(
                action_id=action_id,
                success=False,
                error=msg,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": "PluginNotFoundError"},
            )

        timeout_sec = float(getattr(action, "timeout_seconds", 30.0) or 30.0)
        meta = getattr(action, "metadata", {}) or {}
        params = getattr(action, "parameters", {}) or {}
        action_id = getattr(action, "action_id", "act_0")

        ctx = context or PluginExecutionContext(
            timeout_seconds=timeout_sec,
            metadata=meta,
        )

        try:
            plugin_res: PluginExecutionResult = await self.plugin_manager.aexecute(
                name=target,
                input_data=params,
                context=ctx,
                timeout=timeout_sec,
                raise_on_error=False,
            )

            latency_ms = (
                plugin_res.latency_ms
                if plugin_res.latency_ms > 0
                else round((time.perf_counter() - start_time) * 1000, 2)
            )
            artifacts = self._extract_artifacts(plugin_res.output)

            return ActionResult(
                action_id=action_id,
                success=plugin_res.success,
                output=plugin_res.output,
                error=plugin_res.error,
                latency_ms=latency_ms,
                artifacts=artifacts,
                metadata={
                    "plugin_name": plugin_res.plugin_name,
                    "target": target,
                    **plugin_res.metadata,
                },
            )

        except Exception as err:
            logger.exception("Async error executing action on '%s': %s", target, err)
            action_id = getattr(action, "action_id", "act_0")
            return ActionResult(
                action_id=action_id,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": err.__class__.__name__},
            )

    def _execute_browser(self, action: Action, start_time: float) -> ActionResult:
        """Synchronously execute browser action via browser adapter."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self._aexecute_browser(action, start_time)).result()
            return loop.run_until_complete(self._aexecute_browser(action, start_time))
        except RuntimeError:
            return asyncio.run(self._aexecute_browser(action, start_time))

    async def _aexecute_browser(self, action: Action, start_time: float) -> ActionResult:
        """Asynchronously execute browser action via browser adapter."""
        params = getattr(action, "parameters", {}) or {}
        op = str(params.get("operation") or params.get("action") or "navigate").lower()
        action_id = getattr(action, "action_id", "act_0")
        try:
            if not getattr(self.browser_adapter, "is_active", False):
                if hasattr(self.browser_adapter, "ainitialize"):
                    await self.browser_adapter.ainitialize()
            res_or_coro: Any = None
            if op == "navigate":
                target_url = getattr(action, "target", "")
                url = params.get("url") or params.get("target_url") or (target_url if str(target_url).startswith("http") else None) or "https://google.com"
                res_or_coro = self.browser_adapter.navigate(url)
            elif op == "click":
                selector = params.get("selector", "")
                res_or_coro = self.browser_adapter.click(selector)
            elif op == "type":
                selector = params.get("selector", "")
                text = params.get("text", "")
                res_or_coro = self.browser_adapter.type(selector, text)
            elif op == "screenshot":
                res_or_coro = self.browser_adapter.screenshot()
            elif hasattr(self.browser_adapter, op):
                fn = getattr(self.browser_adapter, op)
                res_or_coro = fn(**{k: v for k, v in params.items() if k not in ("operation", "action")})
            else:
                obs = self.browser_adapter.observe() if hasattr(self.browser_adapter, "observe") else None
                res_or_coro = {"observation": obs}

            if asyncio.iscoroutine(res_or_coro):
                res_data = await res_or_coro
            else:
                res_data = res_or_coro

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ActionResult(
                action_id=action_id,
                success=True,
                output=res_data,
                latency_ms=latency_ms,
                metadata={"target": "browser", "operation": op},
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ActionResult(
                action_id=action_id,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
                metadata={"target": "browser", "operation": op},
            )

    def _extract_artifacts(self, output: Any) -> Dict[str, Any]:
        """Inspect plugin output and extract recognized artifacts."""
        artifacts: Dict[str, Any] = {}
        if output is None:
            return artifacts

        # Coding plugin output with files
        if hasattr(output, "files") and isinstance(output.files, list):
            for f in output.files:
                filename = getattr(f, "file_path", getattr(f, "filename", getattr(f, "path", None)))
                content = getattr(f, "content", None)
                if filename and content is not None:
                    artifacts[f"code:{filename}"] = content

        # Data plugin output with dataset or chart
        if hasattr(output, "dataset") and output.dataset is not None:
            artifacts["dataset"] = output.dataset
        if hasattr(output, "chart") and output.chart is not None:
            artifacts["chart"] = output.chart

        # Website plugin output
        if hasattr(output, "pages") and output.pages:
            artifacts["website_pages"] = output.pages
        if hasattr(output, "preview_url") and output.preview_url:
            artifacts["preview_url"] = output.preview_url

        # Direct dictionary output artifacts
        if isinstance(output, dict):
            if "artifacts" in output and isinstance(output["artifacts"], dict):
                artifacts.update(output["artifacts"])
            for key in ("file", "code", "report", "downloaded_file", "extracted_data"):
                if key in output:
                    artifacts[key] = output[key]

        return artifacts

    def _execute_workspace(self, action: Action, start_time: float) -> ActionResult:
        """Execute workspace intelligence discovery, context, or scan actions."""
        if self.workspace_manager is None:
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error="WorkspaceManager is not configured on AgentExecutor",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": "workspace", "error_type": "WorkspaceNotConfigured"},
            )

        operation = str(action.parameters.get("operation", "discover")).lower()
        try:
            if operation == "discover":
                from xeren.workspace.schemas import DiscoveryRequest
                req = DiscoveryRequest(
                    goal=str(action.parameters.get("goal", "")),
                    preferred_types=action.parameters.get("preferred_types"),
                    search_terms=action.parameters.get("search_terms"),
                    max_candidates=int(action.parameters.get("max_candidates", 10)),
                )
                res = self.workspace_manager.discover(req)
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    output=res.model_dump(),
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    metadata={
                        "target": "workspace",
                        "operation": operation,
                        "candidates_count": len(res.candidates),
                        "selected_count": len(res.selected_candidates),
                        "ambiguity_detected": res.ambiguity_detected,
                    },
                )
            elif operation == "context":
                goal = str(action.parameters.get("goal", ""))
                ctx = self.workspace_manager.build_context(goal)
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    output=ctx.model_dump(),
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    metadata={"target": "workspace", "operation": operation},
                )
            elif operation == "scan":
                scanned = self.workspace_manager.scan()
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    output=[s.model_dump() for s in scanned],
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    metadata={"target": "workspace", "operation": operation, "files_scanned": len(scanned)},
                )
        except Exception as err:
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(err),
                error_code="WORKSPACE_ACTION_ERROR",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": "workspace", "operation": operation},
            )


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
                res = await self.browser.atype_text(selector, text, clear_existing=clear)
                if res.data is None:
                    res.data = {}
                res.data.setdefault("preview", text)
                return res

            elif action_type == "select":
                selector = action.target or action.parameters.get("selector", "")
                value = action.parameters.get("value", "")
                res = await self.browser.aselect_option(selector, value)
                if res.data is None:
                    res.data = {}
                res.data.setdefault("selected_value", value)
                return res

            elif action_type == "scroll":
                direction = action.parameters.get("direction", "down")
                amount = action.parameters.get("amount")
                res = await self.browser.ascroll(direction=direction, amount=amount)
                if res.data is None:
                    res.data = {}
                res.data.setdefault("direction", direction)
                return res

            elif action_type == "extract":
                selector = action.target or action.parameters.get("selector")
                extract_type = action.parameters.get("extract_type", "text")
                res = await self.browser.aextract_content(selector=selector, extract_type=extract_type)
                if res.data is None:
                    res.data = {}
                if "content" not in res.data or not res.data["content"]:
                    res.data["content"] = f"Extracted text: {res.data.get('text', '')}"
                return res

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


__all__ = ["AgentExecutor", "Executor"]
