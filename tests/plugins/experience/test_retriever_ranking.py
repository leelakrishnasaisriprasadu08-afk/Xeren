"""Tests for ExperienceRetrieverTool and ExperienceRankingTool."""

import pytest

from xeren.plugins.experience.schemas import ExperienceItem, UserFeedback
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.tools.ranking import ExperienceRankingTool
from xeren.plugins.experience.tools.retriever import ExperienceRetrieverTool


@pytest.fixture
def store():
    return InMemoryExperienceStore()


@pytest.fixture
def retriever(store):
    return ExperienceRetrieverTool(store=store)


@pytest.fixture
def ranking():
    return ExperienceRankingTool()


def test_retriever_success_and_failure_history(store, retriever):
    """Verify separate retrieval of verified successes and failures."""
    item_success = ExperienceItem(
        task="Read log file",
        selected_plugin="file",
        action="read",
        success=True,
        is_reusable=True,
    )
    item_failure = ExperienceItem(
        task="Write to protected system directory",
        selected_plugin="file",
        action="write",
        success=False,
        failure_reason="Workspace boundary violation",
    )
    store.add(item_success)
    store.add(item_failure)

    successes = retriever.get_success_history()
    assert len(successes) == 1
    assert successes[0].id == item_success.id

    failures = retriever.get_failure_history()
    assert len(failures) == 1
    assert failures[0].id == item_failure.id


def test_retriever_outcome_stats(store, retriever):
    """Verify aggregated outcome tracking statistics calculation."""
    store.add(ExperienceItem(task="Task 1", selected_plugin="coding", success=True, confidence=0.9))
    store.add(ExperienceItem(task="Task 2", selected_plugin="coding", success=True, confidence=0.8))
    store.add(ExperienceItem(task="Task 3", selected_plugin="file", success=False, confidence=0.4))

    stats = retriever.get_stats()
    assert stats.total_count == 3
    assert stats.success_count == 2
    assert stats.failure_count == 1
    assert stats.avg_confidence == 0.7
    assert stats.plugin_breakdown["coding"] == 2
    assert stats.plugin_breakdown["file"] == 1


def test_ranking_multi_factor_scoring(ranking):
    """Verify experiences are ranked combining relevance, outcome quality, and confidence."""
    task = "Parse large JSON dataset file"
    item_irrelevant = ExperienceItem(
        task="Calculate Fibonacci series",
        selected_plugin="coding",
        action="generate",
        success=True,
        confidence=1.0,
    )
    item_relevant_success = ExperienceItem(
        task="Parse large JSON dataset efficiently",
        selected_plugin="data",
        action="inspect",
        success=True,
        verification_status="verified",
        confidence=0.95,
    )
    item_relevant_low_conf = ExperienceItem(
        task="Parse JSON format stream",
        selected_plugin="data",
        action="inspect",
        success=True,
        confidence=0.30,
    )

    ranked, warnings = ranking.rank_experiences(
        experiences=[item_irrelevant, item_relevant_low_conf, item_relevant_success],
        task=task,
    )
    assert len(ranked) == 3
    assert ranked[0].id == item_relevant_success.id


def test_ranking_failure_warning_extraction(ranking):
    """Verify relevant past failures generate structured FailureWarning objects."""
    task = "Delete old project logs"
    failed_exp = ExperienceItem(
        task="Delete old project logs in root",
        selected_plugin="file",
        action="delete",
        success=False,
        failure_reason="Attempted to delete workspace root directory",
        failure_avoidance_advice="Never delete root; specify target subdirectory.",
    )
    success_exp = ExperienceItem(
        task="List directory contents",
        selected_plugin="file",
        action="list",
        success=True,
    )

    ranked, warnings = ranking.rank_experiences(
        experiences=[failed_exp, success_exp],
        task=task,
    )
    assert len(warnings) == 1
    assert warnings[0].failed_action == "delete"
    assert "workspace root" in warnings[0].failure_reason
    assert "Never delete root" in warnings[0].avoidance_advice
