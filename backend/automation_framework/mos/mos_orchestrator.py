"""
Xeren MoS — Main Orchestrator
===============================
The MoSOrchestrator is the top-level brain that replaces the old
single-model Orchestrator. It connects:

  User Input
    ↓
  Main Model (1.5B) — understands user, manages conversation
    ↓ (when specialist help is needed)
  ToolCaller — routes to correct specialist(s)
    ↓
  M1–M12 Specialists — each does their focused job
    ↓
  ToolCaller — aggregates results
    ↓
  Main Model — synthesizes final response
    ↓
  User Response

The old Orchestrator (automation_framework/core/orchestrator.py) handled
everything with plugins. MoSOrchestrator is smarter: it uses the Main
model's reasoning to decide when specialists are needed, then dispatches
intelligently.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from ..core.llm_client import LLMClient
from ..core.base import AutomationResult
from .protocol import (
    AggregatedResponse,
    DispatchRequest,
    RiskLevel,
    TaskStatus,
)
from .specialist_registry import SpecialistRegistry
from .tool_caller import ToolCaller
from .specialist_runner import SpecialistRunner

logger = logging.getLogger("xeren.mos.orchestrator")


# Prompt used to ask the Main model whether specialist routing is needed.
# CRITICAL: reinforces orchestrator role — Main model delegates, does NOT solve.
_ROUTING_PROMPT = """You are Xeren's Main Model. Your role is ORCHESTRATION ONLY.
You understand the user's goal, decide which specialists are needed, and delegate.
You do NOT solve tasks yourself — that is the specialists' job.

User request:
\"\"\"{user_text}\"\"\"

Decide which specialist capabilities are needed. Return JSON with this exact shape:
{{
  "needs_specialists": <true/false>,
  "task_description": "<one sentence: what does the user need done?>",
  "required_capabilities": ["<capability1>", "<capability2>"],
  "allow_parallel": <true/false — true if specialists can work independently>,
  "risk_level": "<low|medium|high>"
}}

Available specialist capabilities: {capabilities}

Orchestration rules:
- needs_specialists = false ONLY for simple greetings, clarifying questions, or pure memory recall.
- needs_specialists = true for ANY task involving reasoning, research, coding, planning, analysis, simulation, verification, or optimization.
- You MUST delegate coding to M7, research to M4, reasoning to M2, planning to M6, etc.
- Do NOT attempt to answer coding/research/math questions yourself in this step.
- allow_parallel = true when specialists can work without depending on each other's output.
- required_capabilities must come from the available list only.
"""

_SYNTHESIS_PROMPT = """You are Xeren's Main Model. Your role at this stage is INTEGRATION.
Your specialists have completed their work. Integrate their findings into a single, clear response.

User's original request:
\"\"\"{user_text}\"\"\"

Specialist findings:
{synthesis}

Your job:
1. Synthesize all specialist outputs into one coherent, helpful response.
2. Do NOT mention "specialists" or "specialist models" — respond as a unified AI assistant.
3. If specialists disagreed or found issues, reconcile them intelligently.
4. Keep the response clear, complete, and directly useful to the user.
"""


class MoSOrchestrator:
    """
    Top-level Mixture-of-Specialists orchestrator for Xeren.
    """

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        tool_caller: Optional[ToolCaller] = None,
        enable_specialists: bool = True,
    ):
        self.llm = llm or LLMClient()
        self._runner = SpecialistRunner(main_llm=self.llm if self.llm.available() else None)
        self.tool_caller = tool_caller or ToolCaller(runner=self._runner)
        self.enable_specialists = enable_specialists

        # Build capability list string for routing prompt
        self._capability_list = ", ".join(
            sorted({cap for s in SpecialistRegistry.enabled() for cap in s.capabilities})
        )
        logger.info("[MoSOrchestrator] initialized (specialists=%s)", enable_specialists)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(self, user_text: str) -> AutomationResult:
        """Synchronous wrapper around async handle."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If inside an async context, run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, self._async_handle(user_text))
                    return future.result()
            else:
                return loop.run_until_complete(self._async_handle(user_text))
        except RuntimeError:
            return asyncio.run(self._async_handle(user_text))

    async def async_handle(self, user_text: str) -> AutomationResult:
        """Async version of handle."""
        return await self._async_handle(user_text)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    async def _async_handle(self, user_text: str) -> AutomationResult:
        t_start = time.monotonic()
        logger.info("[MoSOrchestrator] handling: %s", user_text[:100])

        # Step 1: Ask main model if specialists are needed
        routing = await self._decide_routing(user_text)
        logger.info("[MoSOrchestrator] routing decision: %s", routing)

        if not routing.get("needs_specialists", False) or not self.enable_specialists:
            # Simple conversation — main model handles directly
            logger.info("[MoSOrchestrator] Direct response (no specialists needed)")
            response = await self._direct_response(user_text)
            return AutomationResult(
                summary=response,
                details={"mode": "direct", "routing": routing},
            )

        # Step 2: Dispatch to specialists via ToolCaller
        dispatch_request = DispatchRequest(
            user_query=user_text,
            task_description=routing.get("task_description", user_text),
            required_capabilities=routing.get("required_capabilities", []),
            allow_parallel=routing.get("allow_parallel", True),
            risk_level=RiskLevel(routing.get("risk_level", "low")),
            max_specialists=min(int(routing.get("max_specialists", 3)), 4),
        )

        aggregated: AggregatedResponse = await self.tool_caller.dispatch(dispatch_request)
        logger.info(
            "[MoSOrchestrator] dispatch complete: %d specialists, status=%s",
            aggregated.total_specialists_used,
            aggregated.status,
        )

        # Step 3: Synthesize final response with main model
        if aggregated.status == TaskStatus.SUCCESS and aggregated.synthesis:
            final_response = await self._synthesize(user_text, aggregated.synthesis)
        else:
            final_response = aggregated.recommended_response or "I encountered issues processing this request."

        elapsed_ms = (time.monotonic() - t_start) * 1000
        return AutomationResult(
            summary=final_response,
            details={
                "mode": "mos",
                "routing": routing,
                "trace_id": aggregated.dispatch_trace_id,
                "specialists_used": aggregated.total_specialists_used,
                "execution_ms": elapsed_ms,
                "warnings": aggregated.warnings,
                "specialist_results": [
                    {
                        "id": r.specialist_id,
                        "status": r.status,
                        "confidence": r.confidence,
                        "output_preview": r.output[:200] if r.output else "",
                    }
                    for r in aggregated.specialist_results
                ],
            },
        )

    # ------------------------------------------------------------------
    # Main model prompts
    # ------------------------------------------------------------------

    async def _decide_routing(self, user_text: str) -> Dict[str, Any]:
        """Ask main model to decide if specialists are needed."""
        if not self.llm.available():
            # No LLM available: default to specialist dispatch for non-trivial text
            return {
                "needs_specialists": len(user_text.split()) > 5,
                "task_description": user_text,
                "required_capabilities": [],
                "allow_parallel": True,
                "risk_level": "low",
            }

        prompt = _ROUTING_PROMPT.format(
            user_text=user_text,
            capabilities=self._capability_list,
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.llm.complete_json(prompt))
        return result or {
            "needs_specialists": False,
            "task_description": user_text,
            "required_capabilities": [],
            "allow_parallel": True,
            "risk_level": "low",
        }

    async def _direct_response(self, user_text: str) -> str:
        """Direct main model response for simple requests."""
        if not self.llm.available():
            return f"[Xeren] Received: {user_text} (LLM not available)"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.llm.complete(user_text))

    async def _synthesize(self, user_text: str, synthesis: str) -> str:
        """Ask main model to synthesize specialist outputs into final response."""
        if not self.llm.available():
            return synthesis

        prompt = _SYNTHESIS_PROMPT.format(user_text=user_text, synthesis=synthesis)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.llm.complete(prompt))
