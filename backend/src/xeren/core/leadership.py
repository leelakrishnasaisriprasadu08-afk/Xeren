"""The Royal Triumvirate Leadership Protocol.

Orchestrates the three leadership tiers of Xeren:
  1. 👑 The King (Main Sovereign Model): Communicates with user, makes decisions, issues decrees.
  2. 🧙‍♂️ The Advisor (Reasoning Model): Strategic counsel, chain-of-thought, risk modeling.
  3. ⚔️ The Commander (Execution Engine): Enforces 'Deterministic First' and commands micro-bots.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from xeren.tools.deterministic.fs import default_fs
from xeren.tools.deterministic.system import default_system
from xeren.tools.deterministic.browser import default_browser

logger = logging.getLogger("xeren.core.leadership")


class AdvisorCounsel(BaseModel):
    """Strategic advice and risk assessment produced by the Advisor."""

    counsel_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    reasoning_trace: str = Field(..., description="Deep Chain-of-Thought <think> analysis")
    is_purely_deterministic: bool = Field(default=False, description="True if task requires 0% AI")
    deterministic_action: Optional[str] = Field(default=None, description="Specific deterministic tool to run")
    target_path_or_url: Optional[str] = Field(default=None)
    identified_risks: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    recommended_strategy: str
    suggested_bots: List[str] = Field(default_factory=list)


class KingDecree(BaseModel):
    """The authoritative mandate issued by the King to the Commander."""

    decree_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    approved_strategy: str
    is_purely_deterministic: bool = False
    action_type: str = "execute"
    target: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    assigned_bots: List[str] = Field(default_factory=list)


class CommanderReport(BaseModel):
    """The tactical operation report delivered back to the King."""

    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decree_id: str
    success: bool
    deterministic_actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    ai_bots_invoked: List[str] = Field(default_factory=list)
    deliverable: Any = None
    verification_score: float = 1.0
    latency_ms: float = 0.0
    error: Optional[str] = None


class KingResponse(BaseModel):
    """The final sovereign presentation delivered to the user."""

    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    success: bool
    deliverable: Any = None
    reasoning_summary: Optional[str] = None
    latency_ms: float = 0.0


class LeadershipTriumvirate:
    """Coordinates King, Advisor, and Commander into a closed-loop execution system."""

    def __init__(
        self,
        fs_tools=None,
        system_tools=None,
        browser_tools=None,
    ) -> None:
        self.fs = fs_tools or default_fs
        self.system = system_tools or default_system
        self.browser = browser_tools or default_browser

    def consult_advisor(self, goal: str, context: Optional[Dict[str, Any]] = None) -> AdvisorCounsel:
        """The King consults the Advisor to evaluate logic, risk, and deterministic fast-paths."""
        clean_goal = goal.strip()
        goal_lower = clean_goal.lower()

        # Step 1: Deterministic Check (If possible without AI -> Flag immediately!)
        is_det = False
        det_act = None
        target_item = None
        strategy = ""
        risks = []

        # File reading/listing check
        if any(w in goal_lower for w in ["read file", "open file", "view file", "show content of"]):
            is_det = True
            det_act = "fs.read_file"
            strategy = "Execute local filesystem read operation deterministically."
        elif any(w in goal_lower for w in ["list files", "show files", "list directory", "ls", "dir"]):
            is_det = True
            det_act = "fs.list_dir"
            strategy = "Enumerate directory contents with zero AI hallucination."
        elif any(w in goal_lower for w in ["system stats", "pc info", "laptop specs", "os info", "cpu info"]):
            is_det = True
            det_act = "system.get_stats"
            strategy = "Retrieve local system hardware metrics directly from OS APIs."
        elif any(w in goal_lower for w in ["open tab", "browse to", "navigate to", "open url"]) and any(w in goal_lower for w in ["http://", "https://", "www."]):
            is_det = True
            det_act = "browser.open_tab"
            strategy = "Trigger OS default browser to navigate to target URL."
        elif any(w in goal_lower for w in ["launch", "open app", "start app"]):
            is_det = True
            det_act = "system.open_app"
            strategy = "Invoke OS process launcher for target application."
        else:
            strategy = "Engage multi-step agentic planning with domain micro-bots."

        # Risk Analysis
        if any(w in goal_lower for w in ["delete", "remove", "drop", "destroy", "format", "purge"]):
            risks.append("Action may cause permanent data loss or file modification.")

        think_trace = (
            f"<think>\n"
            f"Goal: '{clean_goal}'\n"
            f"Purely Deterministic: {is_det} (Action: {det_act})\n"
            f"Strategy: {strategy}\n"
            f"Risks Detected: {risks or 'None. Safe operation.'}\n"
            f"</think>"
        )

        return AdvisorCounsel(
            goal=clean_goal,
            reasoning_trace=think_trace,
            is_purely_deterministic=is_det,
            deterministic_action=det_act,
            target_path_or_url=target_item,
            identified_risks=risks,
            recommended_strategy=strategy,
            suggested_bots=["deterministic_engine"] if is_det else ["coding_bot", "research_bot"],
        )

    def issue_decree(self, goal: str, counsel: AdvisorCounsel, context: Optional[Dict[str, Any]] = None) -> KingDecree:
        """The King issues an authoritative operational decree to the Commander."""
        ctx = context or {}
        return KingDecree(
            goal=goal,
            approved_strategy=counsel.recommended_strategy,
            is_purely_deterministic=counsel.is_purely_deterministic,
            action_type=counsel.deterministic_action or "agentic_multibot",
            target=counsel.target_path_or_url or ctx.get("target"),
            parameters=ctx,
            assigned_bots=counsel.suggested_bots,
        )

    def execute_commander(self, decree: KingDecree, counsel: AdvisorCounsel) -> CommanderReport:
        """The Commander marshals resources and executes the mission."""
        start = time.perf_counter()

        # Branch 1: Deterministic First Execution (0% AI Waste)
        if decree.is_purely_deterministic:
            act = decree.action_type
            result_data = None
            success = False
            err = None

            if act == "fs.read_file":
                path = decree.parameters.get("path") or decree.target or "README.md"
                res = self.fs.read_file(path)
                success = res["success"]
                result_data = res.get("content") or res.get("error")
                err = res.get("error")
            elif act == "fs.list_dir":
                path = decree.parameters.get("path") or decree.target or "."
                res = self.fs.list_dir(path)
                success = res["success"]
                result_data = res.get("entries")
                err = res.get("error")
            elif act == "system.get_stats":
                res = self.system.get_system_stats()
                success = res["success"]
                result_data = res
            elif act == "browser.open_tab":
                url = decree.parameters.get("url") or decree.target or "https://xeren.ai"
                res = self.browser.open_tab(url)
                success = res["success"]
                result_data = res.get("message")
                err = res.get("error")
            elif act == "system.open_app":
                app = decree.parameters.get("app") or decree.target or "notepad"
                res = self.system.open_app(app)
                success = res["success"]
                result_data = res.get("message")
                err = res.get("error")
            else:
                success = False
                err = f"Unknown deterministic action: {act}"

            latency = round((time.perf_counter() - start) * 1000, 2)
            return CommanderReport(
                decree_id=decree.decree_id,
                success=success,
                deterministic_actions_taken=[{"action": act, "result": result_data, "error": err}],
                deliverable=result_data,
                verification_score=1.0 if success else 0.0,
                latency_ms=latency,
                error=err,
            )

        # Branch 2: Agentic Micro-Bot Execution & Hybrid Fallback
        from xeren.swarm.fallback_gateway import default_fallback_gateway
        fb_res = default_fallback_gateway.execute_with_fallback(decree.goal, decree.parameters)
        latency = round((time.perf_counter() - start) * 1000, 2)
        return CommanderReport(
            decree_id=decree.decree_id,
            success=fb_res.success,
            ai_bots_invoked=[fb_res.service_used],
            deliverable=fb_res.output or fb_res.data,
            verification_score=1.0 if fb_res.success else 0.0,
            latency_ms=latency,
            error=fb_res.error,
        )

    def synthesize_outcome(self, goal: str, decree: KingDecree, counsel: AdvisorCounsel, report: CommanderReport) -> KingResponse:
        """The King delivers the final sovereign answer to the user with wisdom and clarity."""
        if not report.success:
            content = f"I evaluated your request for '{goal}', but the operation encountered an obstacle: {report.error}."
        else:
            if counsel.is_purely_deterministic:
                content = f"Here is the result for your request:\n\n{report.deliverable}"
            else:
                content = f"I have successfully completed your request for '{goal}'.\n\n{report.deliverable}"

        return KingResponse(
            content=content,
            success=report.success,
            deliverable=report.deliverable,
            reasoning_summary=counsel.recommended_strategy,
            latency_ms=report.latency_ms,
        )

    def process(self, goal: str, context: Optional[Dict[str, Any]] = None) -> KingResponse:
        """Full synchronous cycle of the Royal Triumvirate loop."""
        # 1. King consults Advisor
        counsel = self.consult_advisor(goal, context)
        # 2. King issues Decree
        decree = self.issue_decree(goal, counsel, context)
        # 3. Commander executes
        report = self.execute_commander(decree, counsel)
        # 4. King synthesizes
        return self.synthesize_outcome(goal, decree, counsel, report)


# Singleton
default_triumvirate = LeadershipTriumvirate()

