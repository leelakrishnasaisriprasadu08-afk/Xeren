"""Tests for ConsistencyCheckerTool (contradictions, task alignment, trajectory coherence)."""

import pytest

from xeren.plugins.verification.tools.consistency import ConsistencyCheckerTool


@pytest.fixture
def consistency_tool():
    return ConsistencyCheckerTool()


def test_consistency_internal_contradiction_detected(consistency_tool):
    """Verify internal contradiction detector catches conflicting statements."""
    contradictory_text = (
        "The system connection is always active and stable. "
        "Under current operating conditions, the system connection is never active and impossible to establish."
    )
    checks, score = consistency_tool.check_consistency(candidate=contradictory_text)
    contra_check = next(c for c in checks if c.name == "internal_contradiction_check")
    assert contra_check.passed is False
    assert contra_check.score < 0.5
    assert contra_check.actionable_correction is not None


def test_consistency_coherent_text(consistency_tool):
    """Verify coherent text without contradictions passes."""
    coherent_text = (
        "The background worker started successfully. "
        "It processed 500 queue records and flushed all buffers without errors."
    )
    checks, score = consistency_tool.check_consistency(candidate=coherent_text)
    contra_check = next(c for c in checks if c.name == "internal_contradiction_check")
    assert contra_check.passed is True
    assert contra_check.score == 1.0


def test_consistency_task_alignment(consistency_tool):
    """Verify task alignment matches query keywords and penalizes off-topic responses."""
    task = "Analyze quarterly revenue growth for fiscal year 2025"
    aligned_response = (
        "The quarterly revenue growth for fiscal year 2025 exceeded expectations, "
        "increasing by 14% over baseline projections."
    )
    checks_aligned, score_a = consistency_tool.check_consistency(
        candidate=aligned_response, task=task
    )
    align_check = next(c for c in checks_aligned if c.name == "task_alignment_check")
    assert align_check.passed is True
    assert align_check.score >= 0.70

    # Off-topic response
    off_topic = "Baking chocolate chip cookies requires flour, sugar, butter, and vanilla extract."
    checks_off, score_o = consistency_tool.check_consistency(candidate=off_topic, task=task)
    align_off = next(c for c in checks_off if c.name == "task_alignment_check")
    assert align_off.passed is False
    assert align_off.actionable_correction is not None


def test_consistency_trajectory_coherence(consistency_tool):
    """Verify trajectory coherence detects false success claims when tools failed."""
    trajectory_with_error = [
        {"step": 1, "tool": "search_db", "status": "failed", "error": "ConnectionRefusedError"},
    ]
    false_claim = "Successfully completed all database operations without any issues."

    checks, score = consistency_tool.check_consistency(
        candidate=false_claim, trajectory=trajectory_with_error
    )
    traj_check = next(c for c in checks if c.name == "trajectory_coherence_check")
    assert traj_check.passed is False
    assert "error" in str(traj_check.reason).lower()
    assert traj_check.actionable_correction is not None

    # Clean trajectory passes
    clean_traj = [{"step": 1, "tool": "read_file", "status": "success", "output": "ok"}]
    checks_clean, _ = consistency_tool.check_consistency(
        candidate="The file was read cleanly.", trajectory=clean_traj
    )
    traj_clean = next(c for c in checks_clean if c.name == "trajectory_coherence_check")
    assert traj_clean.passed is True
