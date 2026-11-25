"""Tests for ExperienceRecorderTool (sanitization, deduplication, quality reusability)."""

import pytest

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.tools.recorder import ExperienceRecorderTool
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


@pytest.fixture
def recorder():
    store = InMemoryExperienceStore()
    sanitizer = ExperienceSanitizerTool()
    return ExperienceRecorderTool(store=store, sanitizer=sanitizer)


def test_recorder_basic_save_and_sanitize(recorder):
    """Verify recording sanitizes secrets and persists an experience item."""
    item = ExperienceItem(
        task="Connect with api_key='sk-1234567890abcdef1234567890' to fetch records",
        selected_plugin="research",
        action="web_search",
        outcome="Records fetched successfully",
        success=True,
    )
    saved, was_dedup = recorder.record(item)
    assert was_dedup is False
    assert "sk-" not in saved.task
    assert "[REDACTED]" in saved.task
    assert saved.content_fingerprint != ""
    assert recorder.store.count() == 1


def test_recorder_deduplication(recorder):
    """Verify recording identical experience item updates occurrence count without creating duplicate."""
    item1 = ExperienceItem(
        task="Clean dataframe nulls",
        selected_plugin="data",
        action="clean",
        outcome={"cleaned_rows": 50},
        success=True,
    )
    saved1, dedup1 = recorder.record(item1)
    assert dedup1 is False
    assert recorder.store.count() == 1

    # Record identical experience
    item2 = ExperienceItem(
        task="Clean dataframe nulls",
        selected_plugin="data",
        action="clean",
        outcome={"cleaned_rows": 50},
        success=True,
    )
    saved2, dedup2 = recorder.record(item2)
    assert dedup2 is True
    assert recorder.store.count() == 1
    assert saved2.metadata.get("occurrence_count") == 2


def test_recorder_reusability_guardrails(recorder):
    """Verify failed experiences and low-rated outcomes are marked is_reusable=False."""
    # 1. Failed execution
    failed_item = ExperienceItem(
        task="Execute malicious script",
        selected_plugin="coding",
        action="run",
        outcome="Security Sandbox Blocked",
        success=False,
        failure_reason="Disallowed syscall",
    )
    saved_fail, _ = recorder.record(failed_item)
    assert saved_fail.is_reusable is False
    assert saved_fail.failure_avoidance_advice is not None

    # 2. Verification status failed
    bad_verif = ExperienceItem(
        task="Generate report",
        selected_plugin="website",
        action="generate",
        outcome="Report",
        success=True,
        verification_status="failed",
    )
    saved_bad_verif, _ = recorder.record(bad_verif)
    assert saved_bad_verif.is_reusable is False

    # 3. User feedback poor
    low_rated = ExperienceItem(
        task="Explain quantum entanglement",
        selected_plugin="research",
        action="synthesis",
        outcome="Entanglement means two particles are connected.",
        success=True,
        user_feedback=UserFeedback(rating=1, comments="Inaccurate explanation"),
    )
    saved_low_rated, _ = recorder.record(low_rated)
    assert saved_low_rated.is_reusable is False

    # 4. Verified success is reusable
    good_item = ExperienceItem(
        task="Sort array",
        selected_plugin="coding",
        action="generate",
        outcome="Quick sort",
        success=True,
        verification_status="verified",
        confidence=0.95,
    )
    saved_good, _ = recorder.record(good_item)
    assert saved_good.is_reusable is True
