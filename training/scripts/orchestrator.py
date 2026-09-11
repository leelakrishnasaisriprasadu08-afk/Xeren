"""
Xeren Orchestrator — Central managing system for the Xeren base LLM.

Entry point: python training/scripts/orchestrator.py

The orchestrator does three things on every user message:
  1. CLASSIFY the intent → KNOWN | RESEARCH | CHAT
  2. BUILD context     → inject live state from all sub-system managers
  3. EXECUTE & RESPOND → route through plugins if needed, then generate
                         a confident, grounded reply

Query Modes
-----------
  KNOWN     — model confidence ≥ 0.65 on its own. Answers directly with
               a displayed [confidence: X.XX] score.
  RESEARCH  — unknown territory. Runs 5-strategy plugin pipeline, then
               synthesises a verified conclusion. Never presents raw results.
  CHAT      — casual conversation. Natural, warm, no sub-systems invoked.

Anti-Hallucination Guardrails (all modes)
-----------------------------------------
  • Confidence < 0.65 with no plugin resolution  →  explicit "I don't know yet"
  • Model never fabricates file paths, URLs, system states
  • Live manager context is CLEARLY labelled as "LIVE SYSTEM DATA" in prompts
"""

from __future__ import annotations

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Path bootstrap ───────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent          # Xeren/
_SRC  = _ROOT / "src"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SRC))

from training.scripts.base_wrapper import XerenLocalLLM
from xeren.core.runtime import XerenCore
from xeren.plugins.manager import PluginManager
from xeren.plugins.contract import PluginExecutionContext
from xeren.mcp.manager import MCPManager
from xeren.automation.manager import MultiWorkspaceManager
from xeren.projects.manager import ProjectManager
from xeren.security.gate import XerenSecurityGate
from xeren.security.schemas import DataSensitivityTier
from xeren.security.path_classifier import LLMPathClassifier
from xeren.models.types import ChatMessage

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("xeren.orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD   = 0.65
CHECKPOINT_PATH        = _ROOT / "training" / "checkpoints" / "mini_gpu" / "checkpoint_final.pt"
TOKENIZER_DIR          = _ROOT / "training" / "checkpoints" / "tokenizer"

# Research strategy order (plugin names)
RESEARCH_STRATEGY_ORDER = [
    "research",      # web lookup
    "knowledge",     # internal knowledge base
    "coding",        # code execution / technical verification
    "verification",  # cross-reference / fact check
    "experience",    # stored past patterns
]

# Keywords that suggest CHAT mode (simple conversation)
CHAT_KEYWORDS = {
    "hello", "hi", "hey", "how are you", "good morning", "good evening",
    "good night", "thanks", "thank you", "bye", "goodbye", "ok", "okay",
    "sure", "great", "awesome", "nice", "cool", "haha", "lol",
}

# ─────────────────────────────────────────────────────────────────────────────
# Context Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_system_context(
    plugin_mgr: PluginManager,
    mcp_mgr: MCPManager,
    workspace_mgr: MultiWorkspaceManager,
    project_mgr: ProjectManager,
) -> str:
    """
    Collect live state from all active sub-system managers and format it as a
    clearly labelled LIVE SYSTEM DATA block injected into every LLM prompt.
    """
    lines: List[str] = ["=== LIVE SYSTEM DATA (real-time, injected by Orchestrator) ==="]

    # Active plugins
    plugin_names = plugin_mgr.list_names()
    lines.append(f"[Plugins] Registered ({len(plugin_names)}): {', '.join(plugin_names) or 'none'}")

    # MCP servers
    servers = mcp_mgr.list_servers()
    enabled = [s.name for s in servers if s.enabled]
    lines.append(f"[MCP Servers] Enabled ({len(enabled)}): {', '.join(enabled) or 'none'}")

    # Active freelance orders
    orders = workspace_mgr.list_all_active_orders()
    lines.append(f"[Automation] Active orders: {len(orders)}")
    for o in orders[:3]:  # cap at 3 to avoid token bloat
        lines.append(f"  • Order {o.order_id} [{o.platform.value}] — status: {o.status.value}")

    # Active projects
    projects = project_mgr.list_projects()
    lines.append(f"[Projects] Loaded ({len(projects)}): " +
                 ", ".join(p.name for p in projects[:3]))

    lines.append("=== END LIVE SYSTEM DATA ===")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Query Mode Classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify_mode(user_input: str, confidence: float) -> str:
    """
    Classify the user's message into one of three orchestration modes.

    Returns: "CHAT" | "KNOWN" | "RESEARCH"
    """
    lower = user_input.lower().strip()

    # Distinguish factual inquiries / math / questions from casual smalltalk
    question_starters = (
        "what", "who", "where", "when", "why", "how",
        "is", "are", "can", "could", "explain", "calculate", "tell", "which"
    )
    is_inquiry = (
        lower.endswith("?")
        or any(lower.startswith(q + " ") or lower == q for q in question_starters)
        or any(op in lower for op in ("+", "-", "*", "/", "="))
    )

    if not is_inquiry:
        # CHAT: greetings, pleasantries, casual conversation
        if any(kw in lower for kw in CHAT_KEYWORDS):
            return "CHAT"
        if len(lower) < 15 and not any(char.isdigit() for char in lower):
            return "CHAT"

    # KNOWN: model is confident enough to answer from its own knowledge
    if confidence >= CONFIDENCE_THRESHOLD:
        return "KNOWN"

    # RESEARCH: everything else
    return "RESEARCH"


# ─────────────────────────────────────────────────────────────────────────────
# Device Access (Permission-Gated)
# ─────────────────────────────────────────────────────────────────────────────

def request_device_permission(resource: str, reason: str) -> bool:
    """
    Ask the user for explicit permission before accessing a local file or app.
    Returns True only if user explicitly says yes.
    """
    print(f"\n  ⚠  DEVICE ACCESS REQUEST")
    print(f"     Resource : {resource}")
    print(f"     Reason   : {reason}")
    answer = input("  Allow access? [yes/no] > ").strip().lower()
    return answer in ("yes", "y")


def read_local_file(path: str, security_gate: XerenSecurityGate, user_id: str) -> Optional[str]:
    """Read a local file with permission gate + security classification."""
    if not request_device_permission(path, "LLM wants to read this file for context"):
        print("  [Access Denied — blocked by user]\n")
        return None

    p = Path(path)
    if not p.exists():
        print(f"  [File not found: {path}]\n")
        return None

    decision = security_gate.check_access(
        path=p,
        operation="read",
        user_id=user_id,
        user_intent="User-approved file read for orchestrator context",
    )

    if not decision.is_allowed:
        print(f"  [Security Gate Blocked: {decision.reason}]\n")
        return None

    return p.read_text(encoding="utf-8", errors="replace")


def launch_app(app_name: str, args: List[str] = None) -> bool:
    """Launch a local application after explicit user permission."""
    cmd = [app_name] + (args or [])
    if not request_device_permission(app_name, f"LLM wants to launch: {' '.join(cmd)}"):
        print("  [App Launch Denied — blocked by user]\n")
        return False
    try:
        subprocess.Popen(cmd, shell=True)
        print(f"  [Launched: {' '.join(cmd)}]\n")
        return True
    except Exception as e:
        print(f"  [Launch Failed: {e}]\n")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Research Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_research_pipeline(
    query: str,
    plugin_mgr: PluginManager,
    llm: XerenLocalLLM,
) -> Tuple[str, float]:
    """
    Run through RESEARCH_STRATEGY_ORDER plugins in order.
    Collect results from all that succeed, then ask the LLM to synthesise a
    verified conclusion. Returns (synthesised_answer, final_confidence).
    """
    ctx = PluginExecutionContext(llm=llm)
    collected: List[str] = []

    print("\n  [RESEARCH] Activating multi-strategy plugin pipeline …")

    for strategy_name in RESEARCH_STRATEGY_ORDER:
        if not plugin_mgr.has(strategy_name):
            print(f"    ├─ [{strategy_name}] not registered — skipping")
            continue

        print(f"    ├─ [{strategy_name}] running …", end=" ", flush=True)
        try:
            result = plugin_mgr.execute(
                name=strategy_name,
                input_data={"query": query, "question": query, "text": query, "task": query, "source_code": ""},
                context=ctx,
                timeout=30.0,
            )
            if result.success and result.output:
                snippet = str(result.output)[:400]
                collected.append(f"[{strategy_name.upper()} STRATEGY]\n{snippet}")
                print("✓")
            else:
                print(f"✗ ({result.error or 'no output'})")
        except Exception as exc:
            print(f"✗ (error: {exc})")

    if not collected:
        return (
            "I searched across all available strategies but could not find "
            "enough verified information to answer confidently. "
            "Please try rephrasing or providing more context.",
            0.0,
        )

    # Synthesis prompt: clearly labelled research evidence block
    synthesis_prompt = (
        "=== RESEARCH EVIDENCE (verified by Xeren multi-strategy pipeline) ===\n"
        + "\n\n".join(collected)
        + "\n=== END EVIDENCE ===\n\n"
        f"Based ONLY on the evidence above, provide a clear, accurate, "
        f"and concise answer to: {query}\n"
        "Do not speculate beyond the evidence. "
        "If evidence is contradictory, acknowledge it."
    )

    messages = [
        ChatMessage.system(
            "You are Xeren, an honest AI assistant. "
            "You synthesise verified research results into clear, accurate answers. "
            "You never fabricate facts beyond the evidence provided."
        ),
        ChatMessage.user(synthesis_prompt),
    ]

    response = llm.generate(messages, max_new_tokens=200)
    final_confidence = float(response.metadata.get("confidence", 0.7))
    return response.content, final_confidence


# ─────────────────────────────────────────────────────────────────────────────
# Core Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class XerenOrchestrator:
    """
    Central managing system. Accepts user input, routes to the correct mode,
    and coordinates all sub-system managers under the base LLM's guidance.
    """

    def __init__(self, user_id: str = "local_user") -> None:
        self.user_id = user_id
        self.conversation_history: List[ChatMessage] = []

        # ── Load base LLM ────────────────────────────────────────────────────
        if not CHECKPOINT_PATH.exists():
            raise FileNotFoundError(
                f"Checkpoint not found: {CHECKPOINT_PATH}\n"
                "Run the training pipeline first (scripts 01–05)."
            )
        self.llm = XerenLocalLLM(
            checkpoint_path=CHECKPOINT_PATH,
            tokenizer_dir=TOKENIZER_DIR,
        )

        # ── Sub-system managers ──────────────────────────────────────────────
        print("[Orchestrator] Initialising sub-systems …")
        self.core          = XerenCore(llm=self.llm)
        self.plugin_mgr    = self.core.plugin_manager
        self.mcp_mgr       = MCPManager(load_defaults=True)
        self.workspace_mgr = MultiWorkspaceManager()
        self.project_mgr   = ProjectManager()
        self.security_gate = XerenSecurityGate()
        self.path_classifier = LLMPathClassifier(llm=self.llm, security_gate=self.security_gate)
        print("[Orchestrator] All systems online ✓\n")

    # ── Context helpers ──────────────────────────────────────────────────────

    def _system_context_block(self) -> str:
        return build_system_context(
            self.plugin_mgr,
            self.mcp_mgr,
            self.workspace_mgr,
            self.project_mgr,
        )

    def _build_messages(self, user_input: str, extra_system: str = "") -> List[ChatMessage]:
        """Build the full message list: system context + history + user turn."""
        system_content = (
            "You are Xeren — an honest, helpful AI assistant built from scratch. "
            "You speak naturally and confidently. "
            "You NEVER fabricate facts, file paths, URLs, or system states. "
            "When uncertain, you say so explicitly.\n\n"
            + self._system_context_block()
            + ("\n\n" + extra_system if extra_system else "")
        )
        messages: List[ChatMessage] = [ChatMessage.system(system_content)]
        messages.extend(self.conversation_history[-6:])  # keep last 3 turns
        messages.append(ChatMessage.user(user_input))
        return messages

    # ── Mode handlers ────────────────────────────────────────────────────────

    def _handle_chat(self, user_input: str) -> str:
        """Mode C: natural, warm conversational response."""
        messages = self._build_messages(user_input)
        response = self.llm.generate(messages, max_new_tokens=80, temperature=0.75)
        return response.content

    def _handle_known(self, user_input: str, confidence: float) -> str:
        """Mode A: direct answer with calibrated confidence score."""
        messages = self._build_messages(user_input)
        response = self.llm.generate(messages, max_new_tokens=150, temperature=0.6)
        score = response.metadata.get("confidence", confidence)
        return f"{response.content}\n\n  [confidence: {score:.2f}]"

    def _handle_research(self, user_input: str) -> str:
        """Mode B: multi-strategy research pipeline → verified synthesis."""
        answer, confidence = run_research_pipeline(
            query=user_input,
            plugin_mgr=self.plugin_mgr,
            llm=self.llm,
        )
        if confidence < CONFIDENCE_THRESHOLD and confidence > 0:
            footer = (
                f"\n\n  [confidence: {confidence:.2f}] "
                "⚠ Research completed but certainty is below threshold — "
                "please verify with additional sources."
            )
        elif confidence == 0.0:
            footer = "\n\n  [confidence: 0.00] ✗ No verified results found."
        else:
            footer = f"\n\n  [confidence: {confidence:.2f}] ✓ Verified via research pipeline."
        return answer + footer

    # ── Main process method ──────────────────────────────────────────────────

    def process(self, user_input: str) -> str:
        """
        Full pipeline:
          1. Probe confidence on raw input.
          2. Classify mode.
          3. Handle in the appropriate mode.
          4. Update conversation history.
          5. Return final response string.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        # Quick confidence probe (no generation, just top-token logit)
        probe_messages = self._build_messages(user_input)
        from training.scripts.base_wrapper import _messages_to_chatml
        probe_prompt = _messages_to_chatml(probe_messages)
        confidence = self.llm.compute_confidence(probe_prompt)

        mode = classify_mode(user_input, confidence)
        print(f"  [Mode: {mode}]", end="  ", flush=True)

        t0 = time.perf_counter()

        if mode == "CHAT":
            reply = self._handle_chat(user_input)
        elif mode == "KNOWN":
            reply = self._handle_known(user_input, confidence)
        else:  # RESEARCH
            reply = self._handle_research(user_input)

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        print(f"({elapsed} ms)")

        # Update conversation history
        self.conversation_history.append(ChatMessage.user(user_input))
        self.conversation_history.append(ChatMessage.assistant(reply))

        return reply

    # ── Device shortcuts (permission-gated) ──────────────────────────────────

    def read_file(self, path: str) -> Optional[str]:
        return read_local_file(path, self.security_gate, self.user_id)

    def launch_app(self, app_name: str, args: List[str] = None) -> bool:
        return launch_app(app_name, args)

    def classify_and_store_file(self, path: str, content: str) -> DataSensitivityTier:
        """Classify file content with LLM and store in the correct security vault path."""
        return self.path_classifier.classify_and_store(
            path=path, content=content, user_id=self.user_id
        )


# ─────────────────────────────────────────────────────────────────────────────
# Interactive REPL
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 64)
    print("           XEREN ORCHESTRATOR  — Managing System")
    print("  Base LLM  ·  Plugins  ·  MCP  ·  Security  ·  Projects")
    print("=" * 64)

    try:
        orchestrator = XerenOrchestrator()
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    print("Type your message.  Special commands:")
    print("  :read <path>         — read a local file (permission-gated)")
    print("  :launch <app>        — launch a local application")
    print("  :classify <path>     — classify & store a file into security vault")
    print("  :status              — show sub-system status")
    print("  :exit / :quit        — quit\n")
    print("-" * 64)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # ── Special commands ─────────────────────────────────────────────────
        if user_input.startswith(":exit") or user_input.startswith(":quit"):
            print("Xeren: Goodbye! Stay safe.")
            break

        elif user_input.startswith(":read "):
            path = user_input[6:].strip()
            content = orchestrator.read_file(path)
            if content:
                print(f"\n[File Content — {path}]\n{content[:1000]}")
                # Auto-classify and store
                tier = orchestrator.classify_and_store_file(path, content)
                print(f"[Security] Stored in vault tier: {tier.value}")
            continue

        elif user_input.startswith(":launch "):
            parts = user_input[8:].strip().split()
            orchestrator.launch_app(parts[0], parts[1:] if len(parts) > 1 else [])
            continue

        elif user_input.startswith(":classify "):
            path = user_input[10:].strip()
            content = orchestrator.read_file(path)
            if content:
                tier = orchestrator.classify_and_store_file(path, content)
                print(f"[Security] Classified as: {tier.value}")
            continue

        elif user_input == ":status":
            print("\n[Sub-System Status]")
            print(f"  Plugins  : {orchestrator.plugin_mgr.list_names()}")
            print(f"  MCP      : {[s.name for s in orchestrator.mcp_mgr.list_servers() if s.enabled]}")
            print(f"  Orders   : {len(orchestrator.workspace_mgr.list_all_active_orders())} active")
            print(f"  Projects : {len(orchestrator.project_mgr.list_projects())} loaded")
            print(f"  LLM      : xeren-local (device={orchestrator.llm.device_str})")
            continue

        # ── Normal conversation ──────────────────────────────────────────────
        print("Xeren: ", end="", flush=True)
        reply = orchestrator.process(user_input)
        print(reply)


if __name__ == "__main__":
    main()
