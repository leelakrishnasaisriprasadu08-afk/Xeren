"""
local_runner.py
===============
Unified In-Process Local Multi-Model Runtime for Xeren.

Hosts the Royal Triumvirate on consumer hardware (under 4GB VRAM):
  1. The King (Xeren Sovereign 1.5B) - Master of intent, philosophy, lifelong memory, final conveyance.
  2. The Advisor (DeepSeek-R1-Distill-1.5B) - Deep chain-of-thought <think>, risk analysis, what-if modeling.
  3. The Commander (Qwen2.5-Coder-1.5B) - Multi-task empower engine, 20-bot swarm dispatch, deterministic enforcement.

Features:
  - Sub-5ms in-memory communication bus between leadership tiers.
  - Zero external telemetry: 100% air-gapped local execution.
  - Deterministic-First: 0% AI tokens wasted when native OS/Python can solve the task.
  - Seamless fallback gateway for tasks exceeding local laptop compute.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

def find_project_root() -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur] + list(cur.parents):
        if (p / "pyproject.toml").exists() or (p / "training").exists():
            return p
    return Path.cwd().resolve()

ROOT_DIR = find_project_root()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.core.leadership import (
    AdvisorCounsel,
    CommanderReport,
    KingDecree,
    KingResponse,
    LeadershipTriumvirate,
)
from xeren.swarm.registry import SwarmRegistry, default_swarm_registry
from xeren.swarm.fallback_gateway import (
    CapabilityAssessment,
    FallbackResult,
    HybridFallbackGateway,
    default_fallback_gateway,
)
from xeren.tools.deterministic.fs import DeterministicFileSystem, default_fs
from xeren.tools.deterministic.system import DeterministicSystemTools, default_system
from xeren.tools.deterministic.browser import DeterministicBrowserTools, default_browser


@dataclass
class ModelSlotConfig:
    """Configuration for a specific role in the triumvirate."""
    role: str # "KING", "ADVISOR", "COMMANDER"
    model_name: str
    model_path: Optional[str] = None
    context_window: int = 4096
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class HandoffTrace:
    """Telemetry for an in-memory inter-model communication handoff."""
    sender: str
    receiver: str
    message_type: str
    payload_size_bytes: int
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RuntimeExecutionResult:
    """Complete result returned by the multi-model runtime."""
    user_input: str
    final_response: str
    advisor_counsel: Optional[AdvisorCounsel] = None
    royal_decree: Optional[KingDecree] = None
    commander_report: Optional[CommanderReport] = None
    bot_executions: List[Dict[str, Any]] = field(default_factory=list)
    traces: List[HandoffTrace] = field(default_factory=list)
    total_duration_ms: float = 0.0
    deterministic_first_applied: bool = False
    hybrid_fallback_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_input": self.user_input,
            "final_response": self.final_response,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "deterministic_first_applied": self.deterministic_first_applied,
            "hybrid_fallback_applied": self.hybrid_fallback_applied,
            "advisor": self.advisor_counsel.model_dump() if self.advisor_counsel else None,
            "decree": self.royal_decree.model_dump() if self.royal_decree else None,
            "commander": self.commander_report.model_dump() if self.commander_report else None,
            "bot_executions": self.bot_executions,
            "traces": [
                {
                    "sender": t.sender,
                    "receiver": t.receiver,
                    "type": t.message_type,
                    "latency_ms": round(t.latency_ms, 3),
                }
                for t in self.traces
            ],
        }


class InterModelBus:
    """High-speed in-memory message bus for sub-5ms inter-model handoffs."""

    def __init__(self):
        self._traces: List[HandoffTrace] = []

    def dispatch(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        payload: Any,
    ) -> Tuple[Any, HandoffTrace]:
        t0 = time.perf_counter()
        size_bytes = len(str(payload).encode("utf-8"))
        latency_ms = (time.perf_counter() - t0) * 1000.0

        trace = HandoffTrace(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            payload_size_bytes=size_bytes,
            latency_ms=latency_ms,
        )
        self._traces.append(trace)
        return payload, trace

    @property
    def traces(self) -> List[HandoffTrace]:
        return list(self._traces)

    def clear(self):
        self._traces.clear()


class LocalMultiModelRuntime:
    """
    Unified Orchestrator running the King, Advisor, and Commander.
    Coordinates local models, 20 micro-bots, and deterministic tools.
    """

    def __init__(
        self,
        king_config: Optional[ModelSlotConfig] = None,
        advisor_config: Optional[ModelSlotConfig] = None,
        commander_config: Optional[ModelSlotConfig] = None,
        swarm_registry: Optional[SwarmRegistry] = None,
        fallback_gateway: Optional[HybridFallbackGateway] = None,
    ):
        self.king_config = king_config or ModelSlotConfig(
            role="KING",
            model_name="Xeren-Sovereign-1.5B",
            temperature=0.7,
        )
        self.advisor_config = advisor_config or ModelSlotConfig(
            role="ADVISOR",
            model_name="DeepSeek-R1-Distill-1.5B",
            temperature=0.6,
        )
        self.commander_config = commander_config or ModelSlotConfig(
            role="COMMANDER",
            model_name="Qwen2.5-Coder-1.5B",
            temperature=0.1,
        )

        self.bus = InterModelBus()
        self.swarm = swarm_registry or default_swarm_registry
        self.fallback = fallback_gateway or default_fallback_gateway
        self.leadership = LeadershipTriumvirate(
            fs_tools=default_fs,
            system_tools=default_system,
            browser_tools=default_browser,
        )
        self._discover_local_models()

    def _discover_local_models(self) -> None:
        """Auto-detect downloaded GGUF weights or local checkpoints from manifest."""
        manifest_path = ROOT_DIR / "models/triumvirate/manifest.json"
        if not manifest_path.exists():
            return
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            models = data.get("models", {})
            if "king" in models and models["king"].get("is_downloaded"):
                self.king_config.model_path = models["king"].get("dest_path")
            elif "king" in models and models["king"].get("has_hf_checkpoint"):
                self.king_config.model_path = str(ROOT_DIR / "training/checkpoints/xeren_mini_final")

            if "advisor" in models and models["advisor"].get("is_downloaded"):
                self.advisor_config.model_path = models["advisor"].get("dest_path")

            if "commander" in models and models["commander"].get("is_downloaded"):
                self.commander_config.model_path = models["commander"].get("dest_path")
        except Exception:
            pass


    def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> RuntimeExecutionResult:
        """
        Execute the synchronous Triumvirate loop:
          User -> King -> Advisor -> King -> Commander -> MicroBots/Fallback -> King -> User
        """
        start_time = time.perf_counter()
        self.bus.clear()
        ctx = context or {}
        bot_executions: List[Dict[str, Any]] = []

        # Step 1: User to King
        _, t1 = self.bus.dispatch("USER", "KING", "PROMPT", user_input)

        # Step 2: King consults Advisor
        t_adv_start = time.perf_counter()
        counsel = self.leadership.consult_advisor(user_input, ctx)
        adv_latency = (time.perf_counter() - t_adv_start) * 1000.0
        _, t2 = self.bus.dispatch("KING", "ADVISOR", "CONSULT_REQUEST", user_input)
        _, t3 = self.bus.dispatch("ADVISOR", "KING", "ADVISOR_COUNSEL", counsel)
        t3.latency_ms += adv_latency

        # Step 3: King issues Decree
        t_dec_start = time.perf_counter()
        decree = self.leadership.issue_decree(user_input, counsel, ctx)
        dec_latency = (time.perf_counter() - t_dec_start) * 1000.0
        _, t4 = self.bus.dispatch("KING", "COMMANDER", "ROYAL_DECREE", decree)
        t4.latency_ms += dec_latency

        # Step 4: Commander executes (Deterministic, Micro-Bots, or Hybrid Fallback)
        t_comm_start = time.perf_counter()
        commander_report = self.leadership.execute_commander(decree, counsel)
        comm_latency = (time.perf_counter() - t_comm_start) * 1000.0
        _, t5 = self.bus.dispatch("COMMANDER", "KING", "COMMANDER_REPORT", commander_report)
        t5.latency_ms += comm_latency

        # Capture bot / tool details
        for act in commander_report.deterministic_actions_taken:
            bot_executions.append({
                "type": "deterministic",
                "action": act.get("action"),
                "status": "COMPLETED" if not act.get("error") else "FAILED",
            })
        for bot_id in commander_report.ai_bots_invoked:
            bot_executions.append({
                "type": "agentic_or_fallback",
                "bot_id": bot_id,
                "status": "COMPLETED" if commander_report.success else "FAILED",
            })

        # Step 5: King delivers Sovereign Response to User
        t_king_start = time.perf_counter()
        king_res = self.leadership.synthesize_outcome(user_input, decree, counsel, commander_report)
        king_latency = (time.perf_counter() - t_king_start) * 1000.0
        _, t6 = self.bus.dispatch("KING", "USER", "FINAL_DELIVERABLE", king_res.content)
        t6.latency_ms += king_latency

        total_ms = (time.perf_counter() - start_time) * 1000.0
        hybrid_applied = any("Online" in b.get("bot_id", "") or "Bridge" in b.get("bot_id", "") for b in bot_executions)

        return RuntimeExecutionResult(
            user_input=user_input,
            final_response=king_res.content,
            advisor_counsel=counsel,
            royal_decree=decree,
            commander_report=commander_report,
            bot_executions=bot_executions,
            traces=self.bus.traces,
            total_duration_ms=total_ms,
            deterministic_first_applied=counsel.is_purely_deterministic,
            hybrid_fallback_applied=hybrid_applied,
        )
