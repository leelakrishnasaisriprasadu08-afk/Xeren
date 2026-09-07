"""AgentExecutor executing actions strictly through the existing PluginManager."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from xeren.agent.actions import Action, ActionResult
from xeren.agent.interfaces import Executor
from xeren.plugins.contract import PluginExecutionContext, PluginExecutionResult
from xeren.plugins.errors import (
    PluginError,
    PluginExecutionError,
    PluginNotFoundError,
    PluginTimeoutError,
    PluginValidationError,
)
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.agent.executor")


class AgentExecutor(Executor):
    """Executes actions strictly through the existing Xeren PluginManager.

    Provides plugin failure isolation, timeout handling, artifact extraction,
    and translation into standardized ActionResults.
    """

    def __init__(
        self,
        plugin_manager: PluginManager,
        workspace_manager: Optional[Any] = None,
    ) -> None:
        self.plugin_manager = plugin_manager
        self.workspace_manager = workspace_manager

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
        target = action.target.lower()

        logger.debug("Async executing action '%s' on target '%s'", action.action_id, target)

        if target == "workspace":
            return self._execute_workspace(action, start_time)

        if not self.plugin_manager.has(target):
            available = self.plugin_manager.list_names()
            msg = f"Target plugin '{target}' is not registered in PluginManager. Available: {available}"
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=msg,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": "PluginNotFoundError"},
            )

        ctx = context or PluginExecutionContext(
            timeout_seconds=action.timeout_seconds,
            metadata=action.metadata,
        )

        try:
            plugin_res: PluginExecutionResult = await self.plugin_manager.aexecute(
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

        except Exception as err:
            logger.exception("Async error executing action on '%s': %s", target, err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": target, "error_type": err.__class__.__name__},
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
            else:
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error=f"Unsupported workspace operation: '{operation}'",
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    metadata={"target": "workspace", "operation": operation},
                )
        except Exception as err:
            logger.exception("Workspace execution failed: %s", err)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                metadata={"target": "workspace", "error_type": type(err).__name__},
            )


__all__ = ["AgentExecutor"]

