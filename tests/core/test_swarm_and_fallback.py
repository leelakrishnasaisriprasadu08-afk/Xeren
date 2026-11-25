"""Tests for the 20 Micro-Bots Swarm and Hybrid Online Fallback Gateway."""

import pytest

from xeren.swarm.registry import SwarmRegistry, default_swarm_registry
from xeren.swarm.fallback_gateway import HybridFallbackGateway, default_fallback_gateway
from xeren.core.leadership import default_triumvirate


def test_swarm_registry_loads_20_bots():
    reg = default_swarm_registry
    assert reg.count() == 20

    coding_bots = reg.list_by_cluster("coding")
    assert len(coding_bots) == 5

    research_bots = reg.list_by_cluster("research")
    assert len(research_bots) == 5

    os_bots = reg.list_by_cluster("os")
    assert len(os_bots) == 5

    security_bots = reg.list_by_cluster("security")
    assert len(security_bots) == 5


def test_coding_micro_bots_execution():
    reg = default_swarm_registry

    # 1. React Builder
    react_bot = reg.get("Bot-101-ReactBuilder")
    res = react_bot.execute({"component_name": "UserProfile", "description": "User account badge"})
    assert res.success is True
    assert "export const UserProfile: React.FC<UserProfileProps>" in res.output

    # 2. Syntax Linter on valid vs invalid Python
    linter_bot = reg.get("Bot-105-SyntaxLinter")
    valid_res = linter_bot.execute({"code": "def hello():\n    return 42\n"})
    assert valid_res.success is True
    assert valid_res.verification_passed is True

    invalid_res = linter_bot.execute({"code": "def broken(:\n    return"})
    assert invalid_res.success is False
    assert invalid_res.verification_passed is False
    assert "SyntaxError" in invalid_res.error


def test_security_micro_bots():
    reg = default_swarm_registry

    # 1. Destructive guard
    guard_bot = reg.get("Bot-401-DestructiveGuard")
    blocked_res = guard_bot.execute({"action": "rm -rf / --no-preserve-root"})
    assert blocked_res.success is False
    assert blocked_res.verification_passed is False
    assert "potential irreversible data loss" in blocked_res.error

    safe_res = guard_bot.execute({"action": "python build.py"})
    assert safe_res.success is True

    # 2. Credential sanitizer
    sanitizer_bot = reg.get("Bot-402-CredentialSanitizer")
    redacted = sanitizer_bot.execute({"text": "My secret key is sk-abcdef123456789012345678 and token AIzaSyD1234567890123456789012345678901"})
    assert redacted.success is True
    assert "sk-[REDACTED]" in redacted.output
    assert "AIza[REDACTED]" in redacted.output


def test_hybrid_fallback_gateway_local_vs_online():
    gw = default_fallback_gateway

    # 1. Local execution path
    local_eval = gw.evaluate_capability("Build a React component for user settings")
    assert local_eval.can_execute_locally is True
    assert local_eval.recommended_execution_mode == "local"
    assert local_eval.target_local_bot_id == "Bot-101-ReactBuilder"

    local_exec = gw.execute_with_fallback("Build a React component for user settings")
    assert local_exec.success is True
    assert local_exec.execution_mode == "local"
    assert "UserProfile" in local_exec.output or "interface" in local_exec.output

    # 2. Online fallback path (work that exceeds laptop compute)
    online_eval = gw.evaluate_capability("generate 3d model gltf asset with raytracing")
    assert online_eval.can_execute_locally is False
    assert online_eval.recommended_execution_mode == "online_fallback"

    online_exec = gw.execute_with_fallback("generate 3d model gltf asset with raytracing")
    assert online_exec.success is True
    assert online_exec.execution_mode == "online_fallback"
    assert "remote web compute cluster" in online_exec.output


def test_triumvirate_end_to_end_with_swarm_and_fallback():
    tri = default_triumvirate

    # Ask King for a React component
    response = tri.process("Create a React component for shopping cart")
    assert response.success is True
    assert "React.FC" in response.content or "interface" in response.content
    assert response.latency_ms > 0

