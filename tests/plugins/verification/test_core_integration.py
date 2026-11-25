"""Tests for Verification Plugin integration with XerenCore runtime, health checks, and cross-plugin flows."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.models.providers.mock import MockLLM
from xeren.plugins.contract import PluginHealthStatus
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.verification.schemas import (
    CandidateItem,
    EvidenceItem,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.verification.tools.judge import LLMJudge


def test_core_auto_registers_verification_plugin():
    """Verify XerenCore automatically registers VerificationPlugin alongside all other 6 plugins."""
    core = XerenCore()
    manifests = core.list_plugins()
    plugin_names = {m.name for m in manifests}

    # All 7 plugins must be present
    assert "research" in plugin_names
    assert "knowledge" in plugin_names
    assert "coding" in plugin_names
    assert "website" in plugin_names
    assert "data" in plugin_names
    assert "file" in plugin_names
    assert "verification" in plugin_names

    plugin = core.get_plugin("verification")
    assert isinstance(plugin, VerificationPlugin)


def test_core_set_llm_propagates_to_verification():
    """Verify core.set_llm updates LLM judge in VerificationPlugin."""
    core = XerenCore()
    new_llm = MockLLM(canned_response='{"is_valid": true, "score": 1.0, "rationale": "Updated LLM verdict"}')
    core.set_llm(new_llm)

    verif_plugin = core.get_plugin("verification")
    assert isinstance(verif_plugin, VerificationPlugin)
    assert isinstance(verif_plugin.registry.judge, LLMJudge)
    assert verif_plugin.registry.judge.llm is new_llm


def test_core_verify_method():
    """Verify core.verify() executes synchronous verification."""
    core = XerenCore()
    result = core.verify(
        candidate="The capital of Germany is Berlin.",
        task="What is the capital of Germany?",
        evidence=[EvidenceItem(source_id="geo", content="Berlin is Germany's capital city.", confidence=1.0)],
    )
    assert isinstance(result, VerificationResult)
    assert result.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
    assert result.confidence_score > 0.6


@pytest.mark.asyncio
async def test_core_averify_method():
    """Verify core.averify() executes asynchronous verification."""
    core = XerenCore()
    result = await core.averify(
        candidate="Asynchronous runtime execution test.",
        task="Test async core execution",
    )
    assert isinstance(result, VerificationResult)
    assert result.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)


def test_core_verify_output_method():
    """Verify core.verify_output convenience method for structural validation."""
    core = XerenCore()
    result = core.verify_output(
        candidate='{"valid": true, "items": [1, 2, 3]}',
        expected_format="json",
    )
    assert result.status == VerificationStatus.VERIFIED


def test_core_fact_check_method():
    """Verify core.fact_check convenience method."""
    core = XerenCore()
    # Missing evidence yields UNVERIFIABLE
    res_unverif = core.fact_check(candidate="Unverified medical claim")
    assert res_unverif.status == VerificationStatus.UNVERIFIABLE

    # With evidence
    res_verif = core.fact_check(
        candidate="Water freezes at 0 degrees Celsius under standard atmospheric pressure.",
        evidence=[
            EvidenceItem(
                source_id="physics",
                content="Water freezes at 0 degrees Celsius at 1 atmosphere of pressure.",
                confidence=1.0,
            )
        ],
    )
    assert res_verif.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)


def test_core_rerank_candidates_method():
    """Verify core.rerank_candidates convenience method."""
    core = XerenCore()
    candidates = [
        CandidateItem(id="generic", content="Here is some general information about astronomy."),
        CandidateItem(
            id="specific",
            content="Black holes possess an event horizon beyond which nothing can escape.",
        ),
    ]
    reranked = core.rerank_candidates(
        candidates=candidates,
        task="Explain what an event horizon of a black hole is",
    )
    assert len(reranked) == 2
    assert reranked[0].id == "specific"


def test_core_post_coding_verification_composition():
    """Verify composable workflow: code generation/execution output verified by verification plugin."""
    core = XerenCore()
    python_code = "def fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n"

    # Verify code candidate
    verif_res = core.verify(
        candidate=python_code,
        operation=VerificationOperation.CODE_VERIFICATION,
        task="Implement recursive fibonacci sequence function",
    )
    assert verif_res.status == VerificationStatus.VERIFIED
    assert verif_res.confidence_score >= 0.70


def test_core_post_data_verification_composition():
    """Verify composable workflow: tabular data verified by verification plugin."""
    core = XerenCore()
    tabular_data = [
        {"city": "Tokyo", "population": 14000000},
        {"city": "Paris", "population": 2161000},
    ]

    verif_res = core.verify(
        candidate=tabular_data,
        operation=VerificationOperation.DATA_VERIFICATION,
        schema_definition={
            "type": "array",
        },
    )
    assert verif_res.status == VerificationStatus.VERIFIED


def test_core_health_check_includes_verification():
    """Verify core.check_health() includes healthy status for verification plugin."""
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert "verification" in health["plugins"]
    assert health["plugins"]["verification"]["status"] == PluginHealthStatus.HEALTHY.value
