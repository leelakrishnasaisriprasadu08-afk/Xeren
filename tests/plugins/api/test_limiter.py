"""Rate limiting unit tests for SlidingWindowRateLimiter."""

import time

from xeren.plugins.api.tools.limiter import SlidingWindowRateLimiter


def test_rate_limiter_within_bounds():
    """Verify requests under rate limit threshold are permitted."""
    limiter = SlidingWindowRateLimiter(window_seconds=60.0)
    client_id = "client_alpha"

    for i in range(5):
        allowed, details = limiter.check_rate_limit(client_id, limit_per_minute=10)
        assert allowed is True
        assert details["limit"] == 10
        assert details["remaining"] == 10 - (i + 1)


def test_rate_limiter_exceeded():
    """Verify exceeding rate limit triggers rejection with reset seconds."""
    limiter = SlidingWindowRateLimiter(window_seconds=60.0)
    client_id = "client_burst"

    # Exhaust limit of 3 requests
    for _ in range(3):
        allowed, _ = limiter.check_rate_limit(client_id, limit_per_minute=3)
        assert allowed is True

    # 4th request must be rejected
    allowed, details = limiter.check_rate_limit(client_id, limit_per_minute=3)
    assert allowed is False
    assert details["remaining"] == 0
    assert details["reset_seconds"] > 0.0


def test_rate_limiter_window_expiry():
    """Verify window slides and permits new requests after expiration."""
    # Fast window: 0.1s
    limiter = SlidingWindowRateLimiter(window_seconds=0.1)
    client_id = "client_fast"

    # Fill limit
    limiter.check_rate_limit(client_id, limit_per_minute=1)
    allowed, _ = limiter.check_rate_limit(client_id, limit_per_minute=1)
    assert allowed is False

    # Sleep past window
    time.sleep(0.12)

    # Now allowed again
    allowed_after, _ = limiter.check_rate_limit(client_id, limit_per_minute=1)
    assert allowed_after is True


def test_rate_limiter_reset():
    """Verify manually resetting rate limiter state."""
    limiter = SlidingWindowRateLimiter()
    limiter.check_rate_limit("c1", limit_per_minute=1)
    assert limiter.check_rate_limit("c1", limit_per_minute=1)[0] is False

    limiter.reset("c1")
    assert limiter.check_rate_limit("c1", limit_per_minute=1)[0] is True
