"""Interactive Terminal Chat with the Xeren 7-Stage Autonomous Work Agent.

Run this script to interactively converse with Xeren, ask questions, give automation tasks,
trigger web research, execute OS actions, or test the Learn-First pipeline.

Usage:
    python scripts/chat_agent.py
    python scripts/chat_agent.py --verbose
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from xeren.core.runtime import XerenCore
from xeren.core.hallucination_guard import StructuredAnswer

# ANSI formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


async def main():
    parser = argparse.ArgumentParser(description="Interactive Xeren Agent Chat")
    parser.add_argument("--verbose", "-v", action="store_true", help="Display intermediate stage telemetry")
    args = parser.parse_args()

    print(f"{CYAN}{BOLD}")
    print("=" * 70)
    print("      🚀 XEREN 7-STAGE AUTONOMOUS AGENT - INTERACTIVE CHAT")
    print("      Active Self-Learning | Multi-Root Files | Windows OS | Web")
    print("=" * 70)
    print(f"{RESET}")
    print(f"{DIM}Initializing Xeren Core and autonomous plugins...{RESET}")

    core = XerenCore(auto_register_defaults=True)

    print(f"{GREEN}✔ Xeren Core initialized and ready!{RESET}\n")
    print("Commands:")
    print("  • Type your question or automation request and press Enter.")
    print("  • Type 'verbose' to toggle stage telemetry.")
    print("  • Type 'clear' to reset screen.")
    print("  • Type 'exit' or 'quit' to end the session.\n")
    print(f"{BOLD}{'-' * 70}{RESET}\n")

    verbose = args.verbose
    history = []

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Exiting Xeren session. Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print(f"{YELLOW}Goodbye! Have a productive day.{RESET}")
            break

        if user_input.lower() == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue

        if user_input.lower() == "verbose":
            verbose = not verbose
            print(f"{CYAN}[Telemetry] Verbose mode is now {'ON' if verbose else 'OFF'}.{RESET}")
            continue

        # Check if user is asking for link of a previously generated website/task
        last_action_res = getattr(core, "_last_action_result", None)
        if last_action_res and any(w in user_input.lower() for w in ["link", "url", "where is it", "give link", "show link", "show me the link", "open it"]):
            import re
            final_resp = str(last_action_res.get("final_response", ""))
            links = re.findall(r"(http[s]?://\S+|file://\S+)", final_resp)
            if links:
                clean_link = links[0].rstrip(".)'\"")
                reply = f"Here is the active preview link for your generated website:\n\n🔗 {clean_link}\n\nYou can open this URL directly in your browser to interact with the 3D animated website."
                print(f"{BOLD}{CYAN}Xeren:{RESET}\n{reply}\n")
                history.append((user_input, reply))
                continue

        print(f"\n{DIM}Thinking & orchestrating 7 stages...{RESET}")

        try:
            answer: StructuredAnswer = await core.aanswer_query(user_input)
            if getattr(core, "_last_action_result", None) is None:
                pass

            evidence_sources = getattr(answer, "evidence_sources", getattr(answer, "sources", []))
            status = getattr(answer, "verification_status", "VERIFIED" if getattr(answer, "verified", False) else "PENDING")

            if verbose:
                print(f"{MAGENTA}[Stage Telemetry]{RESET}")
                print(f"  • Stage 1 & 2 Confidence : {answer.confidence_score:.2f}")
                print(f"  • Stage 6 Status         : {status}")
                if evidence_sources:
                    print(f"  • Stage 7 Sources        : {', '.join(evidence_sources[:3])}")
                print()

            print(f"{BOLD}{CYAN}Xeren:{RESET}\n{answer.answer}\n")
            if evidence_sources and not verbose:
                print(f"{DIM}Sources: {', '.join(evidence_sources[:3])}{RESET}\n")

            history.append((user_input, answer.answer))

        except Exception as e:
            print(f"\n{YELLOW}[Error during execution]: {e}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
