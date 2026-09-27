"""Safe retry management, backoff computation, and failure classification tool."""

import logging
from typing import List, Optional, Union

from xeren.plugins.automation.schemas import RetryPolicy, StepStatus, TaskStep

logger = logging.getLogger("xeren.plugins.automation.retry")

DEFAULT_NON_RETRYABLE_PATTERNS: List[str] = [
    "validationerror",
    "validation failed",
    "invalid argument",
    "syntaxerror",
    "syntax error",
    "permission denied",
    "disallowed",
    "security sandbox blocked",
    "path outside workspace",
    "unknown plugin",
]


class RetryManagerTool:
    """Evaluates retry safety, enforces loop guardrails, and calculates backoff delays."""

    def __init__(self, global_max_retries: int = 3) -> None:
        self.global_max_retries = global_max_retries

    def should_retry(
        self,
        step: TaskStep,
        error: Optional[Union[str, Exception]] = None,
        attempt: Optional[int] = None,
    ) -> bool:
        """
        Determine whether a failed step is eligible for another attempt.
        Guarantees bounded retries with zero possibility of infinite loops.
        """
        current_attempts = attempt if attempt is not None else step.retry_count
        max_allowed = min(step.retry_policy.max_retries, self.global_max_retries)
        if current_attempts > max_allowed or (attempt is None and step.retry_count >= max_allowed):
            logger.info(
                "Step '%s' reached maximum allowed retries (%d/%d).",
                step.id,
                current_attempts,
                max_allowed,
            )
            return False

        if error:
            error_str = f"{type(error).__name__}: {error}" if isinstance(error, Exception) else str(error)
            error_lower = error_str.lower()
            # Check step-specific non-retryable errors
            for pattern in step.retry_policy.non_retryable_errors:
                if pattern.lower() in error_lower:
                    logger.info(
                        "Step '%s' encountered non-retryable error pattern '%s': %s",
                        step.id,
                        pattern,
                        error_str,
                    )
                    return False

            # Check default unrecoverable failure patterns
            for pattern in DEFAULT_NON_RETRYABLE_PATTERNS:
                if pattern in error_lower:
                    logger.info(
                        "Step '%s' encountered unrecoverable system failure '%s': %s",
                        step.id,
                        pattern,
                        error_str,
                    )
                    return False

        return True

    def get_backoff_delay(
        self,
        policy: RetryPolicy,
        attempt: int = 1,
        jitter: bool = False,
    ) -> float:
        """Calculate backoff sleep duration in seconds for a specific attempt."""
        interval = policy.initial_interval_seconds
        factor = policy.backoff_factor if policy.backoff_factor >= 1.0 else 1.0
        backoff = interval * (factor ** max(0, attempt - 1))
        ceiling = policy.max_interval_seconds
        capped = min(backoff, ceiling)
        if jitter:
            capped = min(capped * 1.1, ceiling)
        return round(capped, 2)

    def compute_backoff(self, step: TaskStep) -> float:
        """Calculate backoff sleep duration in seconds for the next attempt."""
        return self.get_backoff_delay(step.retry_policy, attempt=step.retry_count + 1)

    def prepare_retry(self, step: TaskStep) -> TaskStep:
        """Increment retry count and reset status to READY for reschedule."""
        return step.model_copy(
            update={
                "retry_count": step.retry_count + 1,
                "status": StepStatus.READY,
                "error": None,
            }
        )


__all__ = ["RetryManagerTool", "DEFAULT_NON_RETRYABLE_PATTERNS"]
