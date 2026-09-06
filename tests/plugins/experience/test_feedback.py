"""Tests for ExperienceFeedbackTool (recalibration, confidence updates, sanitization)."""

import pytest

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.tools.feedback import ExperienceFeedbackTool
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool


@pytest.fixture
def store():
    return InMemoryExperienceStore()


@pytest.fixture
def feedback_tool(store):
    return ExperienceFeedbackTool(store=store, sanitizer=ExperienceSanitizerTool())


def test_feedback_negative_rating_invalidates_reusability(store, feedback_tool):
    """Verify negative feedback (rating <= 2) drops confidence and sets is_reusable=False."""
    item = ExperienceItem(
        task="Summarize contract clause",
        selected_plugin="research",
        action="synthesis",
        outcome="Summary",
        success=True,
        confidence=0.90,
        is_reusable=True,
    )
    store.add(item)

    fb = UserFeedback(rating=1, comments="Completely missed key liability exceptions.")
    updated = feedback_tool.apply_feedback(item.id, fb)
    assert updated is not None
    assert updated.is_reusable is False
    assert updated.confidence <= 0.30
    assert updated.user_feedback.comments == "Completely missed key liability exceptions."

    # Verify persisted in store
    persisted = store.get(item.id)
    assert persisted is not None
    assert persisted.is_reusable is False


def test_feedback_positive_reinforces_confidence(store, feedback_tool):
    """Verify high user rating reinforces confidence."""
    item = ExperienceItem(
        task="Write regex for email",
        selected_plugin="coding",
        action="generate",
        outcome=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        success=True,
        confidence=0.80,
    )
    store.add(item)

    fb = UserFeedback(rating=5, comments="Worked perfectly on all test cases!")
    updated = feedback_tool.apply_feedback(item.id, fb)
    assert updated is not None
    assert updated.confidence >= 0.90
    assert updated.is_reusable is True


def test_feedback_sanitization(store, feedback_tool):
    """Verify sensitive tokens in user feedback comments are sanitized."""
    item = ExperienceItem(task="Auth setup", selected_plugin="file", action="read")
    store.add(item)

    fb = UserFeedback(
        rating=4,
        comments="Used sk-1234567890abcdef1234567890 for testing, succeeded.",
    )
    updated = feedback_tool.apply_feedback(item.id, fb)
    assert updated is not None
    assert "sk-" not in updated.user_feedback.comments
    assert "[REDACTED_API_KEY]" in updated.user_feedback.comments


def test_feedback_non_existent_id(feedback_tool):
    """Verify feedback on missing experience ID returns None."""
    fb = UserFeedback(rating=3)
    res = feedback_tool.apply_feedback("missing_id_999", fb)
    assert res is None
