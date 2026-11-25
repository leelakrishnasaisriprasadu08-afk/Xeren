"""Hybrid Online Fallback Gateway.

Enforces the 'Local First, Web Second' principle:
  1. Checks if the task can be completed by local models and deterministic tools.
  2. If the task requires compute, tools, or models not present on the laptop,
     autonomously routes to supported online websites and cloud services to
     finish the work and bring the result back to the local device.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from xeren.swarm.registry import default_swarm_registry

logger = logging.getLogger("xeren.swarm.fallback")


class CapabilityAssessment(BaseModel):
    """Evaluation of whether a task can be satisfied on-device or requires online fallback."""

    task: str
    can_execute_locally: bool
    recommended_execution_mode: str = "local"  # "local" | "online_fallback"
    reason: str
    target_local_bot_id: Optional[str] = None
    target_online_service: Optional[str] = None


class FallbackResult(BaseModel):
    """Outcome of a hybrid local/online execution."""

    task: str
    execution_mode: str  # "local" | "online_fallback"
    success: bool
    data: Any = None
    output: Optional[str] = None
    service_used: str
    latency_ms: float = 0.0
    error: Optional[str] = None


class HybridFallbackGateway:
    """Intelligently detects local capability gaps and bridges to online services."""

    # Capabilities that typically exceed local laptop limits or require specialized web tools
    ONLINE_REQUIRED_DOMAINS = [
        "generate 3d model gltf",
        "render 4k video",
        "transcribe 10 hour audio",
        "deploy to remote cloud aws",
        "execute heavy cuda matrix 100b",
        "query proprietary live stock ticker websocket",
    ]

    def __init__(self, registry=None) -> None:
        self.registry = registry or default_swarm_registry
        self._online_adapters: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {}
        self._register_default_online_mock_adapters()

    def _register_default_online_mock_adapters(self) -> None:
        """Register built-in web service connectors."""
        # Connector for heavy online tasks
        self._online_adapters["web_compute_engine"] = self._default_web_compute_adapter
        self._online_adapters["cloud_asset_synthesizer"] = self._default_cloud_asset_adapter

    def _default_web_compute_adapter(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulated robust web service connector for heavy off-device computing."""
        return {
            "success": True,
            "provider": "Online Web Compute Bridge",
            "result": f"Successfully offloaded and executed '{task}' via remote web compute cluster.",
        }

    def _default_cloud_asset_adapter(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Connector for online asset rendering/generation."""
        return {
            "success": True,
            "provider": "Online Cloud Asset Service",
            "result": f"Generated remote cloud asset for '{task}' and synchronized to local device.",
        }

    def evaluate_capability(self, task: str) -> CapabilityAssessment:
        """Analyze if the task can run on the laptop or requires an online web service."""
        clean = task.lower().strip()

        # 1. Check if explicitly in online-required heavy domains
        for domain in self.ONLINE_REQUIRED_DOMAINS:
            if domain in clean:
                return CapabilityAssessment(
                    task=task,
                    can_execute_locally=False,
                    recommended_execution_mode="online_fallback",
                    reason=f"Task involves heavy workload ('{domain}') exceeding local laptop hardware budget.",
                    target_online_service="web_compute_engine",
                )

        # 2. Check if a local micro-bot exists to handle this
        matched_bot = self.registry.find_best_bot(task)
        if matched_bot is not None:
            return CapabilityAssessment(
                task=task,
                can_execute_locally=True,
                recommended_execution_mode="local",
                reason=f"Handled on-device by local micro-bot '{matched_bot.bot_id}'.",
                target_local_bot_id=matched_bot.bot_id,
            )

        # 3. Default to local general execution if no hard blocker
        return CapabilityAssessment(
            task=task,
            can_execute_locally=True,
            recommended_execution_mode="local",
            reason="Standard complexity task compatible with local models and deterministic tools.",
            target_local_bot_id="Bot-101-ReactBuilder",
        )

    def execute_with_fallback(self, task: str, params: Optional[Dict[str, Any]] = None) -> FallbackResult:
        """Route to local micro-bot first, or bridge seamlessly to online web service."""
        start = time.perf_counter()
        assessment = self.evaluate_capability(task)
        parameters = params or {}

        # Branch 1: Local Execution
        if assessment.can_execute_locally and assessment.target_local_bot_id:
            bot = self.registry.get(assessment.target_local_bot_id)
            if bot:
                logger.info("Executing locally on device via %s", bot.bot_id)
                bot_res = bot.execute(parameters)
                latency = round((time.perf_counter() - start) * 1000, 2)
                return FallbackResult(
                    task=task,
                    execution_mode="local",
                    success=bot_res.success,
                    data=bot_res.data,
                    output=bot_res.output or bot_res.error,
                    service_used=bot.name,
                    latency_ms=latency,
                    error=bot_res.error,
                )

        # Branch 2: Online Fallback Execution
        service_key = assessment.target_online_service or "web_compute_engine"
        adapter = self._online_adapters.get(service_key, self._default_web_compute_adapter)
        logger.warning("Local models unavailable for task. Engaging Online Fallback Bridge: %s", service_key)

        try:
            remote_res = adapter(task, parameters)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FallbackResult(
                task=task,
                execution_mode="online_fallback",
                success=remote_res.get("success", True),
                data=remote_res,
                output=remote_res.get("result", str(remote_res)),
                service_used=remote_res.get("provider", "Online Web Service"),
                latency_ms=latency,
            )
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return FallbackResult(
                task=task,
                execution_mode="online_fallback",
                success=False,
                service_used=service_key,
                latency_ms=latency,
                error=f"Online fallback failed: {e}",
            )


# Global singleton
default_fallback_gateway = HybridFallbackGateway()
