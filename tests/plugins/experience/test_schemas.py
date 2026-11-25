"""Tests for Experience Plugin schemas, validation bounds, and default values."""

import pytest
from pydantic import ValidationError

from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    ExperienceStats,
    FailureWarning,
    LessonItem,
    OutcomeType,
    UserFeedback,
)


def test_experience_operation_values():
    """Verify all 10 experience operation enum members exist."""
    assert ExperienceOperation.EXPERIENCE_RECORD == "experience_record"
    assert ExperienceOperation.EXPERIENCE_RETRIEVAL == "experience_retrieval"
    assert ExperienceOperation.SUCCESS_HISTORY == "success_history"
    assert ExperienceOperation.FAILURE_HISTORY == "failure_history"
    assert ExperienceOperation.USER_FEEDBACK == "user_feedback"
    assert ExperienceOperation.PATTERN_DETECTION == "pattern_detection"
    assert ExperienceOperation.LESSON_EXTRACTION == "lesson_extraction"
    assert ExperienceOperation.EXPERIENCE_RANKING == "experience_ranking"
    assert ExperienceOperation.FAILURE_AVOIDANCE == "failure_avoidance"
    assert ExperienceOperation.OUTCOME_TRACKING == "outcome_tracking"


def test_outcome_type_values():
    """Verify OutcomeType enum values."""
    assert OutcomeType.SUCCESS == "success"
    assert OutcomeType.PARTIAL_SUCCESS == "partial_success"
    assert OutcomeType.FAILURE == "failure"
    assert OutcomeType.UNKNOWN == "unknown"


def test_user_feedback_schema():
    """Verify UserFeedback fields and rating bounds."""
    fb = UserFeedback(rating=5, thumbs_up=True, comments="Excellent answer!", corrected_outcome=None)
    assert fb.rating == 5
    assert fb.thumbs_up is True
    assert fb.comments == "Excellent answer!"

    # Rating bounds [1, 5]
    with pytest.raises(ValidationError):
        UserFeedback(rating=0)
    with pytest.raises(ValidationError):
        UserFeedback(rating=6)


def test_failure_warning_schema():
    """Verify FailureWarning initialization and bounds."""
    w = FailureWarning(
        task_similarity=0.85,
        failed_action="read_file",
        failed_plugin="file",
        failure_reason="FileNotFoundError: /workspace/missing.py",
        avoidance_advice="Check that the target file exists before reading.",
    )
    assert w.task_similarity == 0.85
    assert w.failed_action == "read_file"
    assert "FileNotFoundError" in w.failure_reason

    with pytest.raises(ValidationError):
        FailureWarning(task_similarity=1.5, failure_reason="err", avoidance_advice="adv")


def test_lesson_item_schema():
    """Verify LessonItem fields and defaults."""
    lesson = LessonItem(
        category="coding",
        pattern="Recursive calls exceed stack limit",
        lesson="Use iterative approaches or increase recursion limit for deep structures.",
        supporting_experiences_count=3,
        confidence=0.92,
    )
    assert lesson.category == "coding"
    assert lesson.supporting_experiences_count == 3
    assert lesson.confidence == 0.92


def test_experience_stats_schema():
    """Verify ExperienceStats schema structure."""
    stats = ExperienceStats(
        total_count=100,
        success_count=85,
        failure_count=15,
        avg_confidence=0.88,
        plugin_breakdown={"coding": 50, "file": 35, "data": 15},
    )
    assert stats.total_count == 100
    assert stats.success_count == 85
    assert stats.plugin_breakdown["coding"] == 50


def test_experience_item_fingerprint():
    """Verify ExperienceItem produces consistent SHA-256 content fingerprints."""
    item1 = ExperienceItem(
        task="Read config file",
        selected_plugin="file",
        action="read_file",
        outcome={"content": "alpha"},
    )
    item2 = ExperienceItem(
        task="Read config file",
        selected_plugin="file",
        action="read_file",
        outcome={"content": "alpha"},
    )
    fp1 = item1.generate_fingerprint()
    fp2 = item2.generate_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex string length


def test_experience_result_serialization():
    """Verify ExperienceResult serializes cleanly to dict."""
    res = ExperienceResult(
        operation=ExperienceOperation.EXPERIENCE_RETRIEVAL,
        success=True,
        experiences=[
            ExperienceItem(task="Task 1", selected_plugin="coding", action="generate")
        ],
        latency_ms=8.5,
    )
    dumped = res.model_dump()
    assert dumped["operation"] == "experience_retrieval"
    assert dumped["success"] is True
    assert len(dumped["experiences"]) == 1
    assert dumped["latency_ms"] == 8.5
