"""Tests for Experience Plugin integration with XerenCore runtime, health checks, and cross-plugin flows."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.contract import PluginHealthStatus
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.schemas import (
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
)
from xeren.plugins.verification.schemas import (
    VerificationOperation,
    VerificationStatus,
)


def test_core_auto_registers_all_eight_plugins():
    """Verify XerenCore automatically registers ExperiencePlugin alongside all other 7 foundational plugins."""
    core = XerenCore()
    manifests = core.list_plugins()
    plugin_names = {m.name for m in manifests}

    assert len(plugin_names) >= 8
    assert "research" in plugin_names
    assert "knowledge" in plugin_names
    assert "coding" in plugin_names
    assert "website" in plugin_names
    assert "data" in plugin_names
    assert "file" in plugin_names
    assert "verification" in plugin_names
    assert "experience" in plugin_names

    plugin = core.get_plugin("experience")
    assert isinstance(plugin, ExperiencePlugin)


def test_core_record_and_retrieve_experience():
    """Verify core.record_experience and core.retrieve_experiences methods."""
    core = XerenCore()
    rec_res = core.record_experience(
        task="Format CSV data into markdown table",
        plugin_name="data",
        action="transform",
        outcome="| Name | Age |\n| Alice | 30 |",
        success=True,
        confidence=0.92,
        lesson="Align markdown table columns with pipes and header separators.",
    )
    assert rec_res.success is True
    assert rec_res.item is not None

    retrieved = core.retrieve_experiences(task="Format CSV data table")
    assert len(retrieved) >= 1
    assert retrieved[0].selected_plugin == "data"


def test_core_get_decision_context():
    """Verify core.get_decision_context returns structured guidance."""
    core = XerenCore()
    core.record_experience(
        task="Deploy React landing page",
        plugin_name="website",
        action="generate",
        success=True,
        lesson="Ensure responsive viewport meta tag is present.",
    )
    core.record_experience(
        task="Deploy React landing page without bundle",
        plugin_name="website",
        action="preview",
        success=False,
        failure_reason="Missing bundle.js in root",
        failure_avoidance_advice="Always build production bundle before starting preview server.",
    )

    context = core.get_decision_context("Deploy React landing page")
    assert context is not None
    assert "SUCCESSFUL PREVIOUS STRATEGIES" in context
    assert "PAST FAILURE WARNINGS" in context


def test_core_add_experience_feedback():
    """Verify core.add_experience_feedback updates experience record."""
    core = XerenCore()
    rec = core.record_experience(
        task="Summarize scientific paper",
        plugin_name="research",
        action="synthesis",
        outcome="Brief summary",
        success=True,
    )
    assert rec.item is not None
    exp_id = rec.item.id

    fb_res = core.add_experience_feedback(
        experience_id=exp_id,
        rating=5,
        thumbs_up=True,
        comments="Great summary, concise and accurate.",
    )
    assert fb_res.success is True
    assert fb_res.item is not None
    assert fb_res.item.user_feedback is not None
    assert fb_res.item.user_feedback.rating == 5


def test_core_get_failure_warnings():
    """Verify core.get_failure_warnings extracts relevant failure advice."""
    core = XerenCore()
    core.record_experience(
        task="Recursive tree traversal on 100k nodes",
        plugin_name="coding",
        action="execute",
        success=False,
        failure_reason="RecursionError: maximum recursion depth exceeded",
        failure_avoidance_advice="Use an explicit stack or iterative queue traversal instead.",
    )

    warnings = core.get_failure_warnings("Recursive tree traversal with large node count")
    assert len(warnings) >= 1
    assert "RecursionError" in warnings[0].failure_reason
    assert "explicit stack" in warnings[0].avoidance_advice


def test_core_closed_loop_verify_and_record():
    """Verify closed-loop execution: verify result with VerificationPlugin then record with ExperiencePlugin."""
    core = XerenCore()
    code = "def is_even(n: int) -> bool:\n    return n % 2 == 0\n"

    # Step 1: Verify code output using VerificationPlugin
    verif_res = core.verify(
        candidate=code,
        operation=VerificationOperation.CODE_VERIFICATION,
        task="Check if integer is even",
    )
    assert verif_res.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)

    # Step 2: Record verified experience
    rec_res = core.record_experience(
        task="Check if integer is even",
        plugin_name="coding",
        action="generate",
        outcome=code,
        success=True,
        verification_status=verif_res.status.value,
        verification_score=verif_res.confidence_score,
        confidence=verif_res.confidence_score,
        lesson="Modulo arithmetic operator % 2 == 0 correctly checks parity.",
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.is_reusable is True


def test_core_health_check_includes_experience():
    """Verify core.check_health() includes experience plugin healthy status."""
    core = XerenCore()
    health = core.check_health()
    assert health["healthy"] is True
    assert "experience" in health["plugins"]
    assert health["plugins"]["experience"]["status"] == PluginHealthStatus.HEALTHY.value
