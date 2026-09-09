"""Unit tests for LLM Self-Improvement Engine, Pattern Recognition, and Adaptive Prompt Evolution."""

import pytest
from fastapi.testclient import TestClient

from xeren.server.app import app
from xeren.models.improvement.engine import LLMSelfImprovementEngine, llm_improvement_engine
from xeren.models.improvement.schemas import ObservationSource


@pytest.fixture
def client():
    return TestClient(app)


def test_engine_pattern_extraction_and_clustering():
    """Test that repeated user queries cluster into patterns and increment frequency."""
    engine = LLMSelfImprovementEngine()

    # Record first query
    engine.record_observation(
        source=ObservationSource.USER_QUERY,
        content="How do I configure Docker containerization for my FastAPI app?",
    )
    patterns_initial = engine.list_patterns()
    pattern_count = len(patterns_initial)

    # Record repeated similar query
    engine.record_observation(
        source=ObservationSource.USER_QUERY,
        content="Docker containerization setup with FastAPI and multi-stage build",
    )
    patterns_after = engine.list_patterns()

    # Find the docker/fastapi pattern
    docker_pattern = next(
        (
            p
            for p in patterns_after
            if any("docker" in q.lower() for q in p.sample_queries)
            or "containerization" in p.intent_cluster
        ),
        None,
    )
    assert docker_pattern is not None
    assert docker_pattern.frequency_count >= 2
    assert len(docker_pattern.sample_queries) >= 2


def test_engine_websearch_and_bot_consensus():
    """Test synthesizing consensus insights and failure traps from web searches."""
    engine = LLMSelfImprovementEngine()

    insight = engine.record_search_insight(
        topic="FastAPI WebSocket Scaling",
        consensus_facts=[
            "Redis Pub/Sub adapter enables horizontal scaling across multiple worker instances.",
            "Heartbeat pings every 30s prevent socket timeouts through load balancers.",
        ],
        recurring_domains=["fastapi.tiangolo.com", "redis.io"],
        failure_traps=["Uncaught connection drops crash event loops without reconnect backoff."],
        bot_models=["Claude 3.5 Sonnet", "Gemini 2.0 Flash"],
    )

    assert insight.insight_id.startswith("smi_")
    assert len(insight.consensus_facts) == 2
    assert insight.recurring_domains == ["fastapi.tiangolo.com", "redis.io"]

    insights_list = engine.list_insights()
    assert any(i.topic == "FastAPI WebSocket Scaling" for i in insights_list)


def test_engine_self_improvement_cycle_and_prompt_augmentation():
    """Test evolving directives and injecting them into the adaptive system prompt."""
    engine = LLMSelfImprovementEngine()

    # Ingest repeated queries to qualify for a new directive
    engine.record_observation(
        source=ObservationSource.USER_QUERY,
        content="Always generate Pydantic v2 schemas with field validators",
    )
    engine.record_observation(
        source=ObservationSource.USER_QUERY,
        content="Pydantic v2 validation models with strict types",
    )

    # Run evolution cycle
    report = engine.run_self_improvement_cycle(force=True)
    assert report.adaptive_score >= 90.0
    assert report.evolution_cycles_completed >= 2

    # Check that directives include active directives
    directives = engine.list_directives()
    assert len(directives) >= 3

    # Check adaptive system prompt addition
    prompt_addition = engine.get_adaptive_system_prompt_addition()
    assert "[XEREN SELF-IMPROVEMENT: ACTIVE ADAPTIVE DIRECTIVES]" in prompt_addition
    assert "CRITICAL DIRECTIVE" in prompt_addition


def test_api_improvement_status_and_patterns(client):
    """Test FastAPI endpoint for self-improvement status and pattern list."""
    status_resp = client.get("/api/llm/improvements/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "ok"
    report = data["report"]
    assert report["adaptive_score"] > 90.0
    assert report["patterns_count"] >= 2
    assert report["active_directives_count"] >= 3

    # Patterns endpoint
    patterns_resp = client.get("/api/llm/improvements/patterns")
    assert patterns_resp.status_code == 200
    patterns = patterns_resp.json()["patterns"]
    assert len(patterns) >= 2
    assert any(p["pattern_id"] == "uqp_collab_isolation" for p in patterns)


def test_api_insights_and_directives_management(client):
    """Test retrieving insights, active directives, and toggling a directive."""
    insights_resp = client.get("/api/llm/improvements/insights")
    assert insights_resp.status_code == 200
    insights = insights_resp.json()["insights"]
    assert len(insights) >= 1
    assert "Distributed Multi-Agent Event Bus" in insights[0]["topic"]

    directives_resp = client.get("/api/llm/improvements/directives")
    assert directives_resp.status_code == 200
    directives = directives_resp.json()["directives"]
    assert len(directives) >= 3

    target_dir = directives[0]
    dir_id = target_dir["directive_id"]

    # Toggle off
    toggle_resp = client.put(
        f"/api/llm/improvements/directives/{dir_id}/toggle",
        json={"is_active": False},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["directive"]["is_active"] is False

    # Toggle back on
    toggle_back = client.put(
        f"/api/llm/improvements/directives/{dir_id}/toggle",
        json={"is_active": True},
    )
    assert toggle_back.status_code == 200
    assert toggle_back.json()["directive"]["is_active"] is True


def test_api_observe_and_analyze(client):
    """Test ingesting an observation via API and triggering self-improvement cycle."""
    obs_resp = client.post(
        "/api/llm/improvements/observe",
        json={
            "source": "user_query",
            "content": "Make sure all API models include description metadata and examples",
            "context": {"user": "@xeren_dev"},
            "outcome_success": True,
        },
    )
    assert obs_resp.status_code == 200
    assert obs_resp.json()["success"] is True

    analyze_resp = client.post(
        "/api/llm/improvements/analyze",
        json={"min_frequency": 1, "force_directive_synthesis": True},
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["success"] is True
    assert "report" in data
    assert data["report"]["adaptive_score"] >= 90.0
