"""End-to-end tests for experience-based learning loop, failure avoidance, and success reuse."""

import pytest

from xeren.core.runtime import XerenCore
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    UserFeedback,
)
from xeren.plugins.verification.schemas import (
    VerificationOperation,
    VerificationStatus,
)


def test_e2e_failure_learning_loop_to_decision_context():
    """
    Test complete failure learning flow:
    failed task -> failure recorded -> lesson preserved/extracted ->
    experience retrievable -> decision context generated ->
    context & warning available for future similar task.
    """
    core = XerenCore()

    # 1. Failed task execution
    task_1 = "Call external payment gateway API"
    action_1 = "api_request"
    failure_reason = "API request failed because authentication was not validated."
    avoidance_advice = "Validate API authentication before executing dependent API operations."
    lesson_1 = "Validate API authentication before executing dependent API operations."

    rec_res = core.record_experience(
        task=task_1,
        plugin_name="research",
        action=action_1,
        outcome="HTTP 401 Unauthorized",
        success=False,
        failure_reason=failure_reason,
        failure_avoidance_advice=avoidance_advice,
        lesson=lesson_1,
        confidence=0.20,
    )

    # 2. Verify failure recorded as first-class experience
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.success is False
    assert rec_res.item.is_reusable is False
    assert rec_res.item.failure_reason == failure_reason
    assert rec_res.item.failure_avoidance_advice == avoidance_advice
    assert rec_res.item.lesson == lesson_1

    # 3. Future similar task arrives
    future_task = "Call external payment gateway API to charge invoice"

    # 4. Decision context generated for Core LLM
    decision_context = core.get_decision_context(future_task)
    assert decision_context is not None
    assert "PAST FAILURE WARNINGS" in decision_context
    assert "authentication was not validated" in decision_context
    assert "Validate API authentication" in decision_context
    assert "RELEVANT LESSONS LEARNED" in decision_context

    # 5. Failure warnings directly accessible
    warnings = core.get_failure_warnings(future_task)
    assert len(warnings) >= 1
    assert "authentication was not validated" in warnings[0].failure_reason
    assert "Validate API authentication" in warnings[0].avoidance_advice


def test_e2e_success_learning_loop_to_decision_context():
    """
    Test complete success learning flow:
    successful task -> verified -> reusable experience/lesson ->
    retrieved for a similar future task -> decision context provided.
    """
    core = XerenCore()

    task_1 = "Write a binary search algorithm in Python"
    code = (
        "def binary_search(arr: list[int], target: int) -> int:\n"
        "    low, high = 0, len(arr) - 1\n"
        "    while low <= high:\n"
        "        mid = low + (high - low) // 2\n"
        "        if arr[mid] == target:\n"
        "            return mid\n"
        "        elif arr[mid] < target:\n"
        "            low = mid + 1\n"
        "        else:\n"
        "            high = mid - 1\n"
        "    return -1\n"
    )

    # 1. Verification of output
    verif = core.verify(
        candidate=code,
        operation=VerificationOperation.CODE_VERIFICATION,
        task=task_1,
    )
    assert verif.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)

    # 2. Record verified experience with lesson
    lesson = "Binary search requires sorted array and midpoint calculation with low + (high - low) // 2."
    rec_res = core.record_experience(
        task=task_1,
        plugin_name="coding",
        action="generate",
        outcome=code,
        success=True,
        verification_status=verif.status.value,
        verification_score=verif.confidence_score,
        confidence=verif.confidence_score,
        lesson=lesson,
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.is_reusable is True
    assert rec_res.item.lesson == lesson

    # 3. Future similar task arrives
    future_task = "Binary search algorithm implementation in Python"

    # 4. Decision context generated with strategy and lesson
    decision_context = core.get_decision_context(future_task)
    assert decision_context is not None
    assert "SUCCESSFUL PREVIOUS STRATEGIES" in decision_context
    assert "Binary search requires sorted array" in decision_context

    # 5. Experience retrievable
    retrieved = core.retrieve_experiences(future_task)
    assert len(retrieved) >= 1
    assert retrieved[0].is_reusable is True
    assert retrieved[0].lesson == lesson


def test_failed_experience_never_marked_reusable():
    """Verify failed experiences are never marked as reusable, even if caller requests it."""
    core = XerenCore()
    rec_res = core.record_experience(
        task="Drop production database table without confirmation",
        plugin_name="data",
        action="execute_query",
        outcome="Safety constraint violation: destructive operation rejected",
        success=False,
        failure_reason="Safety guardrail blocked unverified drop statement",
        confidence=0.0,
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.is_reusable is False

    # Also verify direct ExperienceItem creation with is_reusable=True is corrected by recorder
    plugin = core.get_plugin("experience")
    assert isinstance(plugin, ExperiencePlugin)
    bad_item = ExperienceItem(
        task="Destructive query",
        selected_plugin="data",
        action="delete",
        success=False,
        is_reusable=True,  # Mistakenly set to True
    )
    saved_item, _ = plugin.workflow.registry.recorder_tool.record(bad_item)
    assert saved_item.is_reusable is False


def test_negative_feedback_revokes_reusability():
    """Verify negative user feedback revokes reusability and reduces confidence."""
    core = XerenCore()
    rec_res = core.record_experience(
        task="Generate legal liability disclaimer",
        plugin_name="research",
        action="generate_text",
        outcome="Standard boilerplate disclaimer",
        success=True,
        confidence=0.85,
    )
    assert rec_res.item is not None
    exp_id = rec_res.item.id

    # Add negative 1-star feedback
    fb_res = core.add_experience_feedback(
        experience_id=exp_id,
        rating=1,
        thumbs_up=False,
        comments="Missing statutory warranty exemptions required by state law.",
    )
    assert fb_res.success is True
    assert fb_res.item is not None
    assert fb_res.item.is_reusable is False
    assert fb_res.item.confidence <= 0.30


def test_verified_success_becomes_reusable():
    """Verify verified successful experiences become marked as reusable."""
    core = XerenCore()
    rec_res = core.record_experience(
        task="Compute rolling 7-day average sales",
        plugin_name="data",
        action="transform",
        outcome="Average computed",
        success=True,
        verification_status="verified",
        verification_score=0.95,
        confidence=0.95,
        lesson="Pandas rolling window calculation with min_periods=1 avoids leading nulls.",
    )
    assert rec_res.success is True
    assert rec_res.item is not None
    assert rec_res.item.is_reusable is True
    assert rec_res.item.lesson is not None


def test_failure_warnings_generated_for_relevant_past_failures():
    """Verify failure warnings are generated from relevant past failures."""
    core = XerenCore()
    core.record_experience(
        task="Delete root system files directly",
        plugin_name="file",
        action="delete_path",
        outcome="Permission denied",
        success=False,
        failure_reason="Restricted system path cannot be modified",
        failure_avoidance_advice="Ensure target paths are verified within workspace root.",
    )

    warnings = core.get_failure_warnings("Delete system files under root")
    assert len(warnings) >= 1
    assert "Restricted system path" in warnings[0].failure_reason
    assert "Ensure target paths are verified" in warnings[0].avoidance_advice


def test_lessons_available_in_decision_context():
    """Verify extracted lessons are clearly formatted and available in decision context."""
    core = XerenCore()
    core.record_experience(
        task="Extract tables from unstructured PDF documents",
        plugin_name="data",
        action="ingest",
        outcome="Structured tables",
        success=True,
        verification_status="verified",
        confidence=0.90,
        lesson="OCR bounding box grouping before table parsing avoids misaligned columns.",
    )

    context = core.get_decision_context("Extract tables from PDF invoice document")
    assert context is not None
    assert "RELEVANT LESSONS LEARNED" in context
    assert "OCR bounding box grouping" in context


def test_sensitive_information_sanitized_before_persistence():
    """Verify credentials and secrets are scrubbed before persistence."""
    core = XerenCore()
    secret_key = "sk-1234567890abcdef1234567890abcdef"
    bearer_token = "Bearer secret_jwt_token_1234567890_abcdef"

    rec_res = core.record_experience(
        task=f"Fetch account data using api_key='{secret_key}'",
        plugin_name="research",
        action="fetch",
        context=f"Session header: {bearer_token}",
        outcome=f"Authenticated successfully with {secret_key}",
        success=True,
        confidence=0.85,
    )
    assert rec_res.item is not None
    assert secret_key not in rec_res.item.task
    assert "[REDACTED" in rec_res.item.task
    assert bearer_token not in (rec_res.item.context or "")
    assert secret_key not in str(rec_res.item.outcome)
