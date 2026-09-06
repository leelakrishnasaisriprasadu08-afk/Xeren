"""Tests for ExperiencePatternTool (cluster detection, failure hotspots, lesson distillation)."""

import pytest

from xeren.plugins.experience.schemas import ExperienceItem
from xeren.plugins.experience.tools.patterns import ExperiencePatternTool


@pytest.fixture
def pattern_tool():
    return ExperiencePatternTool()


def test_pattern_detection_high_failure_risk(pattern_tool):
    """Verify tool identifies actions with repeated failures as high risk patterns."""
    experiences = [
        ExperienceItem(
            task="Delete root dir",
            selected_plugin="file",
            action="delete_root",
            success=False,
            failure_reason="Root directory protected",
        ),
        ExperienceItem(
            task="Delete system folder",
            selected_plugin="file",
            action="delete_root",
            success=False,
            failure_reason="Root directory protected",
        ),
    ]
    patterns = pattern_tool.detect_patterns(experiences)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "high_failure_risk"
    assert patterns[0]["target"] == "file:delete_root"
    assert patterns[0]["failure_count"] == 2


def test_pattern_detection_high_reliability(pattern_tool):
    """Verify tool identifies reliable actions as high reliability patterns."""
    experiences = [
        ExperienceItem(task="Read file A", selected_plugin="file", action="read", success=True),
        ExperienceItem(task="Read file B", selected_plugin="file", action="read", success=True),
        ExperienceItem(task="Read file C", selected_plugin="file", action="read", success=True),
    ]
    patterns = pattern_tool.detect_patterns(experiences)
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == "high_reliability"
    assert patterns[0]["target"] == "file:read"
    assert patterns[0]["success_rate"] == 1.0


def test_lesson_extraction_explicit_and_synthesized(pattern_tool):
    """Verify extraction of explicitly recorded lessons and synthesized heuristic rules."""
    experiences = [
        ExperienceItem(
            task="Optimize database query",
            selected_plugin="data",
            action="transform",
            success=True,
            lesson="Add index on foreign key columns before joining large tables.",
            confidence=0.95,
        ),
        ExperienceItem(
            task="Join large datasets",
            selected_plugin="data",
            action="transform",
            success=True,
            lesson="Add index on foreign key columns before joining large tables.",
            confidence=0.90,
        ),
        # Recurring failure
        ExperienceItem(
            task="Parse corrupted CSV",
            selected_plugin="data",
            action="inspect_raw",
            success=False,
            failure_reason="Encoding error",
        ),
        ExperienceItem(
            task="Inspect unknown encoding",
            selected_plugin="data",
            action="inspect_raw",
            success=False,
            failure_reason="Encoding error",
        ),
    ]

    lessons = pattern_tool.extract_lessons(experiences)
    assert len(lessons) >= 2

    # Verify explicit lesson aggregated across 2 experiences
    explicit_lesson = next(
        (l for l in lessons if "foreign key columns" in l.lesson), None
    )
    assert explicit_lesson is not None
    assert explicit_lesson.supporting_experiences_count == 2
    assert explicit_lesson.confidence >= 0.90

    # Verify synthesized failure warning lesson
    fail_lesson = next((l for l in lessons if "data:inspect_raw" in l.lesson), None)
    assert fail_lesson is not None
    assert fail_lesson.category == "data"
