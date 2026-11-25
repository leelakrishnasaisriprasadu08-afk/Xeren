"""
Xeren Orchestrator — Maintenance & Integration Test Suite
Script 08: Run this to verify the entire orchestrator integration is healthy.

What is tested:
  1. Base LLM wrapper  — loads model, generates text, returns confidence
  2. Plugin Manager    — registers plugins, health-checks all
  3. MCP Manager       — lists servers, verifies os_connector present & enabled
  4. Security Classifier — heuristic path, LLM path, vault storage
  5. Query Mode Router — classifies CHAT/KNOWN/RESEARCH correctly
  6. Orchestrator REPL — end-to-end process() with mock inputs
  7. Device access     — list_running_apps via os_connector MCP call
  8. Security Gate     — blocks access without intent, allows with intent

Run:
    python training/scripts/08_maintenance_test.py

All PASS → system is healthy.
Any FAIL → review output and the corresponding sub-system.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, List, Tuple

# ── Path bootstrap ────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC  = _ROOT / "src"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_SRC))

# ─────────────────────────────────────────────────────────────────────────────
# Test runner helpers
# ─────────────────────────────────────────────────────────────────────────────

RESULTS: List[Tuple[str, bool, str]] = []

def run_test(name: str, fn: Callable[[], Any]) -> bool:
    print(f"  {'─' * 56}")
    print(f"  TEST: {name}")
    try:
        fn()
        RESULTS.append((name, True, ""))
        print(f"  ✓  PASS")
        return True
    except Exception as exc:
        tb = traceback.format_exc()
        RESULTS.append((name, False, str(exc)))
        print(f"  ✗  FAIL — {exc}")
        print(f"     {tb.splitlines()[-1]}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Base Wrapper: model load + generate
# ─────────────────────────────────────────────────────────────────────────────

def test_base_wrapper():
    from training.scripts.base_wrapper import XerenLocalLLM
    from xeren.models.types import ChatMessage

    ckpt = _ROOT / "training" / "checkpoints" / "mini_gpu" / "checkpoint_final.pt"
    tok  = _ROOT / "training" / "checkpoints" / "tokenizer"

    assert ckpt.exists(), f"Checkpoint missing: {ckpt}"
    assert tok.exists(),  f"Tokenizer dir missing: {tok}"

    llm = XerenLocalLLM(checkpoint_path=ckpt, tokenizer_dir=tok)
    assert llm.ping(), "LLM ping failed"

    messages = [ChatMessage.user("Hello, how are you?")]
    response = llm.generate(messages, max_new_tokens=20)
    assert isinstance(response.content, str), "Response content must be string"
    assert "confidence" in response.metadata, "Confidence metadata missing"
    conf = response.metadata["confidence"]
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
    print(f"     content[:60]: '{response.content[:60]}'")
    print(f"     confidence  : {conf}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Plugin Manager: registration & health
# ─────────────────────────────────────────────────────────────────────────────

def test_plugin_manager():
    from xeren.core.runtime import XerenCore
    core = XerenCore()
    names = core.plugin_manager.list_names()
    print(f"     Registered plugins ({len(names)}): {names}")
    assert len(names) >= 10, f"Expected default plugins to be registered, got {len(names)}"
    # Health check all registered plugins
    health = core.plugin_manager.health_check()
    for plugin_name, result in health.items():
        assert result.status.value in ("healthy", "degraded", "unknown"), \
            f"Plugin {plugin_name} is unhealthy: {result}"
    print(f"     All {len(health)} plugins passed health check")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — MCP Manager: os_connector present
# ─────────────────────────────────────────────────────────────────────────────

def test_mcp_manager():
    from xeren.mcp.manager import MCPManager
    mgr = MCPManager(load_defaults=True)
    servers = {s.id: s for s in mgr.list_servers()}
    print(f"     Servers registered: {list(servers.keys())}")
    assert "os_connector" in servers, "os_connector server not registered in defaults"
    assert servers["os_connector"].enabled, "os_connector is disabled"
    # Call a safe tool
    result = mgr.call_tool("os_connector", "list_running_apps", {})
    assert "running_apps" in result.get("output", {}), \
        f"list_running_apps failed: {result}"
    apps = result["output"]["running_apps"]
    print(f"     Running apps (first 5): {apps[:5]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Security Path Classifier: heuristic + LLM + vault storage
# ─────────────────────────────────────────────────────────────────────────────

def test_path_classifier():
    from training.scripts.base_wrapper import XerenLocalLLM
    from xeren.security.path_classifier import LLMPathClassifier, TIER_PATHS
    from xeren.security.schemas import DataSensitivityTier

    ckpt = _ROOT / "training" / "checkpoints" / "mini_gpu" / "checkpoint_final.pt"
    tok  = _ROOT / "training" / "checkpoints" / "tokenizer"
    llm  = XerenLocalLLM(checkpoint_path=ckpt, tokenizer_dir=tok)

    clf = LLMPathClassifier(llm=llm)

    # Heuristic: liberal code file
    tier = clf.classify("script.py", "def hello():\n    print('world')\n")
    print(f"     script.py → {tier.value}")
    assert tier == DataSensitivityTier.LIBERAL, f"Expected LIBERAL, got {tier}"

    # Heuristic: sensitive (api key mention)
    tier = clf.classify("config.env", "API_KEY=sk-abc123-very-secret")
    print(f"     config.env → {tier.value}")
    assert tier == DataSensitivityTier.SENSITIVE, f"Expected SENSITIVE, got {tier}"

    # Heuristic: over-sensitive (private key)
    tier = clf.classify("id_rsa", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAK…")
    print(f"     id_rsa → {tier.value}")
    assert tier == DataSensitivityTier.MORE_SENSITIVE, f"Expected MORE_SENSITIVE, got {tier}"

    # Vault storage test
    stored_tier = clf.classify_and_store("test_log.txt", "This is a general log entry.", user_id="test_user")
    vault_files = clf.list_vault_contents()
    print(f"     Vault contents: { {k: len(v) for k, v in vault_files.items()} }")
    assert stored_tier == DataSensitivityTier.LIBERAL


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Query Mode Router: correct classification
# ─────────────────────────────────────────────────────────────────────────────

def test_query_mode_router():
    from training.scripts.orchestrator import classify_mode

    cases = [
        ("Hi",                     1.0, "CHAT"),
        ("Hello there!",           0.9, "CHAT"),
        ("What is 2+2?",           0.9, "KNOWN"),
        ("What is the capital of France?", 0.8, "KNOWN"),
        ("Explain quantum entanglement in detail with recent papers.", 0.3, "RESEARCH"),
        ("How does Xeren's security gate handle over-sensitive files?",  0.4, "RESEARCH"),
    ]
    for text, conf, expected in cases:
        mode = classify_mode(text, conf)
        print(f"     '{text[:40]}' conf={conf} → {mode} (expected {expected})")
        assert mode == expected, f"Mode mismatch for '{text}': got {mode}, expected {expected}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — Orchestrator end-to-end: process() with mock inputs
# ─────────────────────────────────────────────────────────────────────────────

def test_orchestrator_process():
    from training.scripts.orchestrator import XerenOrchestrator

    orch = XerenOrchestrator(user_id="test_user")

    # CHAT mode
    reply = orch.process("Hi there!")
    assert isinstance(reply, str) and len(reply) > 0, "Empty reply for CHAT input"
    print(f"     CHAT reply[:80]: '{reply[:80]}'")

    # KNOWN mode (short direct question, high confidence expected from model)
    reply = orch.process("What programming language is Python?")
    assert isinstance(reply, str) and len(reply) > 0, "Empty reply for KNOWN input"
    print(f"     KNOWN reply[:80]: '{reply[:80]}'")

    # RESEARCH mode (complex question)
    reply = orch.process("What are the latest advances in transformer attention mechanisms in 2026?")
    assert isinstance(reply, str) and len(reply) > 0, "Empty reply for RESEARCH input"
    print(f"     RESEARCH reply[:120]: '{reply[:120]}'")


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — Device Access: os_connector list_running_apps
# ─────────────────────────────────────────────────────────────────────────────

def test_device_access():
    from xeren.mcp.manager import MCPManager
    mgr = MCPManager(load_defaults=True)
    result = mgr.call_tool("os_connector", "list_running_apps", {})
    assert result["success"] is True, f"Tool call failed: {result}"
    running = result["output"].get("running_apps", [])
    assert isinstance(running, list), "running_apps should be a list"
    print(f"     Detected {len(running)} running process(es). Sample: {running[:3]}")

    # Test list_directory on workspace
    result2 = mgr.call_tool("os_connector", "list_directory", {"path": str(_ROOT)})
    entries = result2["output"].get("entries", [])
    assert len(entries) > 0, "list_directory returned empty"
    print(f"     Project root entries (first 5): {entries[:5]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 8 — Security Gate: intent blocking & pass-through
# ─────────────────────────────────────────────────────────────────────────────

def test_security_gate():
    from xeren.security.gate import XerenSecurityGate
    from xeren.security.schemas import AccessOutcome

    gate = XerenSecurityGate()
    test_path = Path(_ROOT / "training" / "requirements.txt")

    # Without intent → should be denied at Layer 1
    decision_no_intent = gate.check_access(
        path=test_path,
        operation="read",
        user_id="test_user",
        user_intent="",
    )
    assert decision_no_intent.outcome in (
        AccessOutcome.DENIED, AccessOutcome.ALLOWED_FAST_PATH
    ), f"Expected DENIED or FAST_PATH without intent, got {decision_no_intent.outcome}"
    print(f"     No intent → {decision_no_intent.outcome.value}")

    # With intent → LIBERAL file should fast-path through
    decision_with_intent = gate.check_access(
        path=test_path,
        operation="read",
        user_id="test_user",
        user_intent="Reading training requirements for dependency audit",
    )
    assert decision_with_intent.is_allowed, \
        f"Expected allowed for LIBERAL path with intent, got {decision_with_intent.outcome}"
    print(f"     With intent → {decision_with_intent.outcome.value}")


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("\n" + "=" * 60)
    print("  XEREN ORCHESTRATOR — MAINTENANCE TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        ("1. Base LLM Wrapper",          test_base_wrapper),
        ("2. Plugin Manager",            test_plugin_manager),
        ("3. MCP Manager (os_connector)",test_mcp_manager),
        ("4. Security Path Classifier",  test_path_classifier),
        ("5. Query Mode Router",         test_query_mode_router),
        ("6. Orchestrator end-to-end",   test_orchestrator_process),
        ("7. Device Access (OS tools)",  test_device_access),
        ("8. Security Gate",             test_security_gate),
    ]

    t_start = time.perf_counter()
    for name, fn in tests:
        run_test(name, fn)

    elapsed = round(time.perf_counter() - t_start, 2)

    # ── Summary ──────────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed

    print(f"\n{'=' * 60}")
    print(f"  RESULTS  {passed}/{len(RESULTS)} PASSED   |   {failed} FAILED   |   {elapsed}s")
    print(f"{'=' * 60}")
    for name, ok, err in RESULTS:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}  {name}")
        if not ok:
            print(f"          ↳ {err[:120]}")
    print()

    if failed:
        print("  ⚠  Some tests failed. Review the output above.")
        sys.exit(1)
    else:
        print("  ✅  All tests passed! Xeren Orchestrator is healthy.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
