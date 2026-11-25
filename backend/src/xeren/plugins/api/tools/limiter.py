"""Rate limiting interface and sliding-window in-memory implementation."""

from abc import ABC, abstractmethod
from collections import defaultdict, deque
import threading
import time
from typing import Any, Dict, Optional, Tuple


class BaseRateLimiter(ABC):
    """Abstract interface defining rate limiting policies for API consumers."""

    @abstractmethod
    def check_rate_limit(
        self, identifier: str, limit_per_minute: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check whether an incoming request from an identifier (API key ID or IP) is allowed.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
            where rate_limit_info contains:
            - limit: total allowed per window
            - remaining: remaining requests in current window
            - reset_seconds: seconds until window resets
        """
        pass


class SlidingWindowRateLimiter(BaseRateLimiter):
    """Thread-safe sliding-window rate limiter tracking timestamps in a 60-second window."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._history: Dict[str, deque[float]] = defaultdict(deque)

    def check_rate_limit(
        self, identifier: str, limit_per_minute: int
    ) -> Tuple[bool, Dict[str, Any]]:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._history[identifier]
            # Prune timestamps outside current sliding window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            count = len(timestamps)
            if count >= limit_per_minute:
                # Oldest timestamp + window determines reset time
                oldest = timestamps[0] if timestamps else now
                reset_seconds = max(0.0, round((oldest + self.window_seconds) - now, 2))
                return False, {
                    "limit": limit_per_minute,
                    "remaining": 0,
                    "reset_seconds": reset_seconds,
                }

            # Record this request
            timestamps.append(now)
            remaining = max(0, limit_per_minute - (count + 1))
            return True, {
                "limit": limit_per_minute,
                "remaining": remaining,
                "reset_seconds": round(self.window_seconds, 2),
            }

    def reset(self, identifier: Optional[str] = None) -> None:
        """Reset rate limits for a specific identifier or clear all history."""
        with self._lock:
            if identifier:
                self._history.pop(identifier, None)
            else:
                self._history.clear()


__all__ = ["BaseRateLimiter", "SlidingWindowRateLimiter"]
