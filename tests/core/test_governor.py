"""Tests for AdaptiveUsageGovernor and high-concurrency transaction traffic controller."""

import asyncio
import time
import pytest

from xeren.core.governor import (
    AdaptiveUsageGovernor,
    AdmissionResult,
    TrafficVerdict,
    UserTokenBucket,
)


@pytest.mark.asyncio
async def test_normal_admission():
    """Verify normal traffic within quota is immediately allowed."""
    governor = AdaptiveUsageGovernor(
        default_user_capacity=10.0,
        default_user_refill_rate=5.0,
    )
    result = await governor.evaluate("user_1", cost=1.0)
    assert result.verdict == TrafficVerdict.ALLOWED
    assert result.remaining_tokens == 9.0
    headers = result.to_headers()
    assert headers["X-RateLimit-Limit"] == "10"
    assert headers["X-RateLimit-Remaining"] == "9"


@pytest.mark.asyncio
async def test_micro_burst_smoothing_delay():
    """Verify sudden micro-burst is smoothed with non-blocking delay instead of error."""
    governor = AdaptiveUsageGovernor(
        default_user_capacity=5.0,
        default_user_refill_rate=10.0,  # 10 tokens/sec
    )
    # Drain bucket to 0
    await governor.evaluate("burst_user", cost=5.0)

    # Next call needs 1 token, deficit is ~1.0, delay = 1.0 / 10 = 0.1s <= 0.5s -> SMOOTHED_DELAY
    res = await governor.evaluate("burst_user", cost=1.0)
    assert res.verdict == TrafficVerdict.SMOOTHED_DELAY
    assert 0.0 < res.delay_seconds <= 0.5
    assert "micro-delaying" in res.reason


@pytest.mark.asyncio
async def test_severe_exhaustion_cache_routing():
    """Verify severe quota overages are routed to CAG cache instead of hard failure."""
    governor = AdaptiveUsageGovernor(
        default_user_capacity=2.0,
        default_user_refill_rate=0.5,  # slow refill
    )
    await governor.evaluate("heavy_user", cost=2.0)

    # Deficit is ~2.0, delay = 2.0 / 0.5 = 4.0s > 0.5s -> DEGRADED_SERVE_CACHE
    res = await governor.evaluate("heavy_user", cost=2.0)
    assert res.verdict == TrafficVerdict.DEGRADED_SERVE_CACHE
    assert res.retry_after_seconds > 0.0
    assert "CAG" in res.reason


@pytest.mark.asyncio
async def test_cluster_high_load_cache_routing():
    """Verify that when cluster load exceeds 85%, requests route to zero-compute cache."""
    governor = AdaptiveUsageGovernor(
        max_concurrent_requests=10,
        cluster_high_load_threshold=0.8,
    )
    # Artificially set 9 active in-flight requests (90% load)
    for _ in range(9):
        await governor.acquire_concurrency()

    try:
        res = await governor.evaluate("any_user", cost=1.0)
        assert res.verdict == TrafficVerdict.DEGRADED_SERVE_CACHE
        assert "near peak capacity" in res.reason
    finally:
        for _ in range(9):
            governor.release_concurrency()


@pytest.mark.asyncio
async def test_load_shedding_under_queue_saturation():
    """Verify that if global queue depth is saturated, load is gracefully shed."""
    governor = AdaptiveUsageGovernor(
        max_queue_depth=5,
    )
    governor._queue_depth = 10  # simulate saturated queue

    res = await governor.evaluate("overflow_user", cost=1.0)
    assert res.verdict == TrafficVerdict.SHED_LOAD
    assert res.retry_after_seconds == 3.0
    headers = res.to_headers()
    assert "Retry-After" in headers


@pytest.mark.asyncio
async def test_memory_pruning_under_massive_user_tracking():
    """Verify governor evicts expired/old users to guarantee bounded memory over 1 week."""
    governor = AdaptiveUsageGovernor(
        max_tracked_users=50,
        user_ttl_seconds=0.05,  # 50ms TTL for testing
    )
    # Register 40 users
    for i in range(40):
        await governor.evaluate(f"client_{i}", cost=0.1)

    assert len(governor._user_buckets) == 40
    await asyncio.sleep(0.06)

    # Adding more triggers pruning
    for i in range(40, 65):
        await governor.evaluate(f"client_{i}", cost=0.1)

    # Should have evicted stale clients and kept tracked_users <= max_tracked_users
    assert len(governor._user_buckets) <= 50


@pytest.mark.asyncio
async def test_concurrency_pacing_and_telemetry():
    """Verify acquire/release and real-time telemetry metrics."""
    governor = AdaptiveUsageGovernor(
        max_concurrent_requests=100,
    )
    await governor.acquire_concurrency()
    assert governor.in_flight == 1
    assert governor.load_factor == 0.01

    governor.release_concurrency()
    assert governor.in_flight == 0

    telemetry = governor.get_telemetry()
    assert "active_in_flight" in telemetry
    assert "load_factor" in telemetry
    assert "current_rps" in telemetry
    assert "total_admitted" in telemetry


@pytest.mark.asyncio
async def test_high_concurrency_1000_spike_simulation():
    """Simulate 1,000 rapid concurrent transactions with zero exceptions or race-conditions."""
    governor = AdaptiveUsageGovernor(
        default_user_capacity=50.0,
        default_user_refill_rate=25.0,
        max_concurrent_requests=200,
    )

    async def _worker(client_id: int):
        admission = await governor.evaluate(f"sim_client_{client_id % 20}", cost=1.0)
        assert admission.verdict in (
            TrafficVerdict.ALLOWED,
            TrafficVerdict.SMOOTHED_DELAY,
            TrafficVerdict.DEGRADED_SERVE_CACHE,
            TrafficVerdict.SHED_LOAD,
        )
        if admission.verdict == TrafficVerdict.ALLOWED:
            await governor.acquire_concurrency()
            await asyncio.sleep(0.001)
            governor.release_concurrency()

    tasks = [_worker(i) for i in range(1000)]
    await asyncio.gather(*tasks)

    # Governor handled all 1000 with zero unhandled exceptions
    tel = governor.get_telemetry()
    total_handled = tel["total_admitted"] + tel["total_smoothed"] + tel["total_cache_routed"] + tel["total_shed"]
    assert total_handled == 1000
    assert governor.in_flight == 0
