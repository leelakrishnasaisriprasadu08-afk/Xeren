"""Efficiency, Throughput, and Latency Benchmark Tests for LLM Self-Improvement Engine."""

import time
import pytest
from fastapi.testclient import TestClient

from xeren.server.app import app
from xeren.models.improvement.engine import LLMSelfImprovementEngine
from xeren.models.improvement.schemas import ObservationSource


@pytest.fixture
def client():
    return TestClient(app)


def test_prompt_augmentation_latency_sub_millisecond():
    """Verify that injecting active adaptive directives into LLM reasoning prompt is sub-millisecond."""
    engine = LLMSelfImprovementEngine()

    # Warm-up call
    _ = engine.get_adaptive_system_prompt_addition()

    iterations = 1000
    start_time = time.perf_counter()
    for _ in range(iterations):
        prompt_addition = engine.get_adaptive_system_prompt_addition()
        assert "ACTIVE ADAPTIVE DIRECTIVES" in prompt_addition
    duration = time.perf_counter() - start_time

    avg_latency_ms = (duration / iterations) * 1000
    print(f"\n[BENCHMARK] Prompt Augmentation Latency: {avg_latency_ms:.4f} ms per call ({iterations} iterations)")
    
    # Assert average latency is well under 1.0 ms (typically 0.005 - 0.02 ms)
    assert avg_latency_ms < 1.0, f"Prompt augmentation took {avg_latency_ms:.3f}ms, exceeds 1.0ms threshold!"


def test_query_clustering_throughput_benchmark():
    """Verify high-throughput observation ingestion and clustering (hundreds of queries in milliseconds)."""
    engine = LLMSelfImprovementEngine()

    test_queries = [
        "How do I set up FastAPI WebSocket multiplexing for collaborative workstations?",
        "WebSocket multiplexing with FastAPI and Redis pubsub scaling",
        "How to isolate project workstation sessions for multiple team members?",
        "Collaborative project workspace session isolation and zero interruptions",
        "Configure MongoDB Atlas connection verification and latency ping",
        "MongoDB verification with roundtrip latency test and Atlas M0 free tier",
        "TypeScript React 19 component design with dark glassmorphism",
        "React 19 modern UI components with responsive glassmorphic cards",
    ]

    # Ingest 400 queries (50 batches of 8 queries)
    total_queries = 400
    start_time = time.perf_counter()
    for i in range(50):
        for q in test_queries:
            engine.record_observation(
                source=ObservationSource.USER_QUERY,
                content=f"{q} #{i}",
            )
    elapsed = time.perf_counter() - start_time
    queries_per_sec = total_queries / elapsed
    avg_per_query_ms = (elapsed / total_queries) * 1000

    print(f"\n[BENCHMARK] Clustering Throughput: {queries_per_sec:.1f} queries/sec ({elapsed:.4f}s for {total_queries} queries, {avg_per_query_ms:.4f}ms/query)")

    # Assert processing rate exceeds 1,000 queries/sec (avg < 1.0ms per ingestion)
    assert queries_per_sec > 1000.0, f"Throughput too low: {queries_per_sec:.1f} queries/sec"

    # Verify clustering occurred properly
    patterns = engine.list_patterns()
    assert len(patterns) >= 4
    for p in patterns:
        if any("websocket" in q.lower() for q in p.sample_queries):
            assert p.frequency_count >= 50


def test_web_search_and_consensus_synthesis_efficiency():
    """Verify that multi-model consensus and failure trap extraction performs efficiently under load."""
    engine = LLMSelfImprovementEngine()

    iterations = 200
    start_time = time.perf_counter()
    for i in range(iterations):
        engine.record_search_insight(
            topic=f"Distributed Consensus Topic #{i % 10}",
            consensus_facts=[
                "Fact 1: Explicit schemas eliminate serialization ambiguity.",
                "Fact 2: Reconnection backoff prevents cascading connection storm.",
            ],
            recurring_domains=["fastapi.tiangolo.com", "developer.mozilla.org", "react.dev"],
            failure_traps=["Uncaught websocket close terminates async task without cleanup."],
            bot_models=["Claude 3.5 Sonnet", "Gemini 2.0 Flash", "Strawberry CoT"],
        )
    elapsed = time.perf_counter() - start_time
    avg_ms = (elapsed / iterations) * 1000
    print(f"\n[BENCHMARK] Web/Bot Insight Recording: {avg_ms:.4f} ms per insight ({iterations} iterations)")

    assert avg_ms < 1.0, f"Recording search insight too slow: {avg_ms:.3f} ms"
    assert len(engine.list_insights()) >= iterations


def test_evolution_cycle_synthesis_runtime():
    """Verify that running the full self-improvement synthesis cycle is fast and non-blocking."""
    engine = LLMSelfImprovementEngine()

    # Pre-populate 50 queries across various intents
    for i in range(50):
        engine.record_observation(
            source=ObservationSource.USER_QUERY,
            content=f"Docker containerization build configuration pattern #{i}",
        )

    start_time = time.perf_counter()
    report = engine.run_self_improvement_cycle(force=True)
    duration_ms = (time.perf_counter() - start_time) * 1000

    print(f"\n[BENCHMARK] Full Evolution Cycle Runtime: {duration_ms:.2f} ms")
    assert duration_ms < 100.0, f"Evolution cycle took too long: {duration_ms:.2f} ms"
    assert report.adaptive_score > 0
    assert report.evolution_cycles_completed >= 2


def test_api_endpoint_latency_benchmark(client: TestClient):
    """Benchmark end-to-end FastAPI endpoint response times for self-improvement APIs."""
    # Warm up
    client.get("/api/llm/improvements/status")

    iterations = 100
    # 1. Status endpoint latency
    start = time.perf_counter()
    for _ in range(iterations):
        res = client.get("/api/llm/improvements/status")
        assert res.status_code == 200
    status_avg_ms = ((time.perf_counter() - start) / iterations) * 1000

    # 2. Observe endpoint latency
    start = time.perf_counter()
    for i in range(iterations):
        res = client.post(
            "/api/llm/improvements/observe",
            json={
                "source": "user_query",
                "content": f"How do I optimize database query indexing #{i}?",
            },
        )
        assert res.status_code == 200
    observe_avg_ms = ((time.perf_counter() - start) / iterations) * 1000

    print(f"\n[BENCHMARK] API Status Endpoint Latency: {status_avg_ms:.2f} ms/req")
    print(f"[BENCHMARK] API Ingestion Endpoint Latency: {observe_avg_ms:.2f} ms/req")

    # Both endpoints should respond in under 15ms per request on local loopback
    assert status_avg_ms < 15.0, f"Status endpoint latency too high: {status_avg_ms:.2f} ms"
    assert observe_avg_ms < 15.0, f"Observe endpoint latency too high: {observe_avg_ms:.2f} ms"
