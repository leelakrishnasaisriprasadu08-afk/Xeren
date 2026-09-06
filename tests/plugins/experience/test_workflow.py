"""Tests for ExperienceWorkflow routing all 10 experience operations."""

import pytest

from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    UserFeedback,
)
from xeren.plugins.experience.workflow import ExperienceWorkflow


@pytest.fixture
def workflow():
    return ExperienceWorkflow()


def test_workflow_record_and_retrieve(workflow):
    """Verify EXPERIENCE_RECORD and EXPERIENCE_RETRIEVAL end-to-end workflow."""
    rec_inp = ExperienceInput(
        operation=ExperienceOperation.EXPERIENCE_RECORD,
        task="Write a fast sorting function in Python",
        plugin_name="coding",
        action="generate",
        outcome="def quicksort(arr): ...",
        success=True,
        confidence=0.95,
        lesson="Quicksort with median pivot avoids worst case O(n^2).",
    )
    rec_res = workflow.run(rec_inp)
    assert rec_res.operation == ExperienceOperation.EXPERIENCE_RECORD
    assert rec_res.success is True
    assert rec_res.item is not None

    # Retrieve
    ret_inp = ExperienceInput(
        operation=ExperienceOperation.EXPERIENCE_RETRIEVAL,
        task="Sort an array with fast performance",
    )
    ret_res = workflow.run(ret_inp)
    assert ret_res.operation == ExperienceOperation.EXPERIENCE_RETRIEVAL
    assert len(ret_res.experiences) == 1
    assert "quicksort" in ret_res.decision_context.lower()


def test_workflow_success_and_failure_history(workflow):
    """Verify SUCCESS_HISTORY and FAILURE_HISTORY operations."""
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Valid action",
            plugin_name="file",
            action="read",
            success=True,
        )
    )
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Invalid action",
            plugin_name="file",
            action="delete",
            success=False,
            failure_reason="Access denied",
        )
    )

    success_res = workflow.run(
        ExperienceInput(operation=ExperienceOperation.SUCCESS_HISTORY)
    )
    assert len(success_res.experiences) == 1
    assert success_res.experiences[0].success is True

    failure_res = workflow.run(
        ExperienceInput(operation=ExperienceOperation.FAILURE_HISTORY)
    )
    assert len(failure_res.experiences) == 1
    assert failure_res.experiences[0].success is False


def test_workflow_user_feedback(workflow):
    """Verify USER_FEEDBACK operation modifies target experience."""
    rec_res = workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Answer medical question",
            plugin_name="research",
            success=True,
        )
    )
    exp_id = rec_res.item.id

    fb_res = workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.USER_FEEDBACK,
            experience_id=exp_id,
            user_feedback=UserFeedback(rating=5, comments="Accurate!"),
        )
    )
    assert fb_res.success is True
    assert fb_res.item.user_feedback.rating == 5


def test_workflow_pattern_detection(workflow):
    """Verify PATTERN_DETECTION operation."""
    for i in range(2):
        workflow.run(
            ExperienceInput(
                operation=ExperienceOperation.EXPERIENCE_RECORD,
                task=f"Fail task {i}",
                plugin_name="coding",
                action="unsafe_run",
                success=False,
                failure_reason="Segfault",
            )
        )
    pat_res = workflow.run(
        ExperienceInput(operation=ExperienceOperation.PATTERN_DETECTION)
    )
    assert pat_res.success is True
    assert len(pat_res.metadata.get("patterns", [])) >= 1


def test_workflow_lesson_extraction(workflow):
    """Verify LESSON_EXTRACTION operation."""
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Data pipeline",
            plugin_name="data",
            action="clean",
            success=True,
            lesson="Always validate timestamp formats before grouping.",
        )
    )
    lesson_res = workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.LESSON_EXTRACTION,
            task="Data pipeline",
        )
    )
    assert lesson_res.success is True
    assert len(lesson_res.lessons) >= 1
    assert "timestamp formats" in lesson_res.lessons[0].lesson


def test_workflow_ranking(workflow):
    """Verify EXPERIENCE_RANKING operation."""
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Parse YAML file",
            plugin_name="file",
            action="read",
            success=True,
        )
    )
    rank_res = workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RANKING,
            task="Read YAML configuration",
        )
    )
    assert rank_res.success is True
    assert len(rank_res.experiences) >= 1


def test_workflow_failure_avoidance(workflow):
    """Verify FAILURE_AVOIDANCE operation."""
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Delete root system directory",
            plugin_name="file",
            action="delete",
            success=False,
            failure_reason="Restricted directory access",
            failure_avoidance_advice="Specify explicit file path inside workspace.",
        )
    )
    avoid_res = workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.FAILURE_AVOIDANCE,
            task="Delete system directory",
        )
    )
    assert avoid_res.success is True
    assert len(avoid_res.failure_warnings) >= 1
    assert "Restricted directory" in avoid_res.failure_warnings[0].failure_reason


def test_workflow_outcome_tracking(workflow):
    """Verify OUTCOME_TRACKING operation."""
    workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Task 1",
            plugin_name="research",
            success=True,
        )
    )
    stats_res = workflow.run(
        ExperienceInput(operation=ExperienceOperation.OUTCOME_TRACKING)
    )
    assert stats_res.success is True
    assert stats_res.stats.total_count >= 1


@pytest.mark.asyncio
async def test_workflow_arun(workflow):
    """Verify asynchronous workflow execution."""
    inp = ExperienceInput(
        operation=ExperienceOperation.EXPERIENCE_RECORD,
        task="Async workflow task",
        plugin_name="coding",
        action="test",
        success=True,
    )
    res = await workflow.arun(inp)
    assert isinstance(res, ExperienceResult)
    assert res.success is True
    assert res.latency_ms >= 0.0
