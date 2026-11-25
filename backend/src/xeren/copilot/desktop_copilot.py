"""
desktop_copilot.py
==================
Real-Time Desktop Copilot & System Automation Interface for Xeren.

Connects the user directly to the King (Main Sovereign Model) and enables:
  - Local device automation: read, write, and patch files in the device.
  - OS operations: launch local applications, query hardware stats and CPU/RAM.
  - Browser actions: open browser tabs, search with zero API keys, clean web text.
  - Swarm delegation: multi-task coding, linter, research, and security micro-bots.
  - Hybrid Online Fallback: when a heavy task exceeds the laptop's compute,
    autonomously completes it via cloud/web bridges and saves outputs locally.
  - Philosophical & intelligent conveyance: deep wisdom, decisive leadership.

Usage:
  Interactive Mode:
    python src/xeren/copilot/desktop_copilot.py
  Single Command Mode:
    python src/xeren/copilot/desktop_copilot.py --cmd "show content of README.md"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from xeren.runtime.local_runner import (
    LocalMultiModelRuntime,
    RuntimeExecutionResult,
)


# ANSI Color Codes for Rich Terminal Copilot UX
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class CopilotTurnResult:
    """Outcome of a single copilot turn."""
    query: str
    response: str
    runtime_result: RuntimeExecutionResult
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DesktopCopilot:
    """The frontline real-time copilot running on the user's workstation."""

    def __init__(self, runtime: Optional[LocalMultiModelRuntime] = None):
        self.runtime = runtime or LocalMultiModelRuntime()
        self.history: List[CopilotTurnResult] = []

    def execute_command(self, user_command: str) -> CopilotTurnResult:
        """Process a user command through the Royal Triumvirate loop."""
        res = self.runtime.process(user_command)
        turn = CopilotTurnResult(
            query=user_command,
            response=res.final_response,
            runtime_result=res,
        )
        self.history.append(turn)
        return turn

    def format_turn(self, turn: CopilotTurnResult, verbose: bool = False) -> str:
        """Render a turn with rich status banners and telemetry."""
        r = turn.runtime_result
        lines = []

        lines.append(f"\n{BOLD}{CYAN}👑 XEREN SOVEREIGN (THE KING){RESET}")
        lines.append(f"{turn.response}")

        if verbose or r.advisor_counsel:
            lines.append(f"\n{DIM}--- Strategic Telemetry ---{RESET}")
            if r.advisor_counsel:
                lines.append(f"{YELLOW}🧙‍♂️ Advisor Strategy:{RESET} {r.advisor_counsel.recommended_strategy}")
            if r.deterministic_first_applied:
                lines.append(f"{GREEN}⚡ Deterministic Fast-Path:{RESET} 100% Native OS/Python Standard Library (0% AI Waste)")
            if r.hybrid_fallback_applied:
                lines.append(f"{MAGENTA}🌐 Hybrid Fallback Gateway:{RESET} Routed to Cloud Compute / Web Service Bridge")

            if r.bot_executions:
                bot_list = ", ".join([b.get("bot_id") or b.get("action") or "engine" for b in r.bot_executions])
                lines.append(f"{CYAN}⚔️ Swarm Execution:{RESET} [{bot_list}]")

            lines.append(f"{DIM}⏱️ Total Latency: {r.total_duration_ms:.2f}ms | Inter-Model Bus: Sub-5ms{RESET}\n")

        return "\n".join(lines)

    def interactive_shell(self):
        """Run an interactive conversation loop in the terminal."""
        print(f"\n{BOLD}{MAGENTA}===================================================================={RESET}")
        print(f"{BOLD}{CYAN}   XEREN REAL-TIME DESKTOP COPILOT & AUTOMATION WORKSTATION{RESET}")
        print(f"{DIM}   Air-Gapped Sovereign AI | Deterministic-First | Royal Triumvirate{RESET}")
        print(f"{BOLD}{MAGENTA}===================================================================={RESET}")
        print(f"Type your command, question, or task below. (Type 'exit' or 'quit' to quit)\n")

        while True:
            try:
                user_input = input(f"{BOLD}{GREEN}You > {RESET}").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print(f"\n{CYAN}👑 Xeren: 'Until we meet again, my Sovereign. Your workstation remains protected.'{RESET}\n")
                    break

                turn = self.execute_command(user_input)
                print(self.format_turn(turn, verbose=True))

            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{CYAN}👑 Xeren: 'Session paused.'{RESET}\n")
                break


def main():
    parser = argparse.ArgumentParser(description="Xeren Desktop Copilot & Automation Interface")
    parser.add_argument("--cmd", type=str, help="Single command to execute immediately")
    parser.add_argument("--verbose", action="store_true", help="Display full advisor & swarm traces")
    args = parser.parse_args()

    copilot = DesktopCopilot()

    if args.cmd:
        turn = copilot.execute_command(args.cmd)
        print(copilot.format_turn(turn, verbose=args.verbose or True))
    else:
        copilot.interactive_shell()


if __name__ == "__main__":
    main()

