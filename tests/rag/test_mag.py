"""Unit tests for Memory-Augmented Generation (MAG) cognitive memory subsystem."""

import time
import pytest

from xeren.rag.mag.engine import MAGRetrievalEngine
from xeren.rag.mag.types import MemoryQuery, MemoryTier


def test_mag_remember_and_retrieve_working_memory() -> None:
    engine = MAGRetrievalEngine()
    engine.record_working_constraint("Always output JSON responses", session_id="sess_123")

    query = MemoryQuery(query_text="output format JSON", session_id="sess_123")
    results = engine.retrieve(query)

    assert len(results) == 1
    assert results[0].record.tier == MemoryTier.WORKING
    assert "JSON" in results[0].record.content
    assert results[0].importance == 0.9
    assert results[0].score > 0.5


def test_mag_session_isolation_for_working_memory() -> None:
    engine = MAGRetrievalEngine()
    engine.record_working_constraint("Session 1 specific goal", session_id="sess_1")
    engine.record_working_constraint("Session 2 specific goal", session_id="sess_2")

    # Query within session 1
    q1 = MemoryQuery(query_text="specific goal", session_id="sess_1")
    r1 = engine.retrieve(q1)
    assert len(r1) == 1
    assert "Session 1" in r1[0].record.content

    # Query within session 2
    q2 = MemoryQuery(query_text="specific goal", session_id="sess_2")
    r2 = engine.retrieve(q2)
    assert len(r2) == 1
    assert "Session 2" in r2[0].record.content


def test_mag_user_correction_highest_priority() -> None:
    engine = MAGRetrievalEngine()
    engine.remember("Standard default behavior is to use tabs", tier=MemoryTier.EPISODIC, importance=0.4)
    engine.record_user_correction("Never use tabs, always use 4 spaces for Python", session_id="sess_100")

    query = MemoryQuery(query_text="tabs or spaces for Python indentation", min_score=0.1)
    results = engine.retrieve(query)

    assert len(results) >= 1
    # The user correction has importance=1.0 and should rank highest
    top = results[0]
    assert "4 spaces" in top.record.content
    assert top.importance == 1.0


def test_mag_exponential_recency_decay() -> None:
    current_time = 100000.0

    def mock_time() -> float:
        return current_time

    engine = MAGRetrievalEngine(time_provider=mock_time, default_half_life_hours=10.0)
    engine.remember("User prefers dark mode UI", tier=MemoryTier.EPISODIC, importance=0.8)

    # Immediately after creation (t = 0 elapsed)
    q = MemoryQuery(query_text="dark mode UI preference", min_score=0.01, half_life_hours=10.0)
    initial_results = engine.retrieve(q)
    assert len(initial_results) == 1
    score_fresh = initial_results[0].score

    # Advance time by 10 hours (1 half-life: decay factor should be ~0.5)
    current_time += 10.0 * 3600.0
    half_life_results = engine.retrieve(q)
    assert len(half_life_results) == 1
    score_decayed = half_life_results[0].score

    assert pytest.approx(score_decayed, rel=0.05) == score_fresh * 0.5


def test_mag_get_memory_context_formatting() -> None:
    engine = MAGRetrievalEngine()
    engine.record_working_constraint("Limit response to 2 sentences", session_id="s1")
    engine.record_semantic_fact("Repository uses strict typing with MyPy", importance=0.9)

    context_str = engine.get_memory_context("typing response", session_id="s1")
    assert "--- BEGIN COGNITIVE MEMORY CONTEXT (MAG) ---" in context_str
    assert "Limit response to 2 sentences" in context_str
    assert "Repository uses strict typing" in context_str
    assert "--- END COGNITIVE MEMORY CONTEXT ---" in context_str


def test_mag_session_consolidation_to_semantic() -> None:
    engine = MAGRetrievalEngine()
    engine.record_working_constraint("Crucial architectural invariant", session_id="session_final")

    # Consolidate session
    consolidated = engine.consolidate_session_to_semantic("session_final", min_importance=0.8)
    assert consolidated == 1

    # Verify that a semantic memory was generated
    semantic_ids = engine._tier_index[MemoryTier.SEMANTIC]
    assert len(semantic_ids) >= 1
    semantic_record = next(r for r in engine._records.values() if r.tier == MemoryTier.SEMANTIC)
    assert "Crucial architectural invariant" in semantic_record.content


def test_mag_clear_working_memory() -> None:
    engine = MAGRetrievalEngine()
    engine.record_working_constraint("Working task A", session_id="sA")
    engine.record_working_constraint("Working task B", session_id="sB")

    cleared = engine.clear_working_memory(session_id="sA")
    assert cleared == 1

    remaining = engine.get_memory_context("task", session_id="sB")
    assert "Working task B" in remaining

    cleared_check = engine.get_memory_context("task", session_id="sA")
    assert "Working task A" not in cleared_check
