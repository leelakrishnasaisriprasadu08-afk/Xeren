"""Tests for RetryManagerTool: bounded retry evaluation, exponential backoff, and non-retryable error detection."""

from xeren.plugins.automation.schemas import RetryPolicy, TaskStep
from xeren.plugins.automation.tools.retry import RetryManagerTool


def test_retry_manager_attempt_bounds():
    """Verify retries are allowed up to max_retries and rejected beyond."""
    manager = RetryManagerTool()
    step = TaskStep(
        id="s1",
        plugin_name="data",
        action="fetch",
        retry_policy=RetryPolicy(max_retries=2),
    )

    # Attempt 0 (first try failed, attempt counter 1)
    assert manager.should_retry(step, attempt=1, error=RuntimeError("connection reset")) is True
    # Attempt 1 (second try failed, attempt counter 2)
    assert manager.should_retry(step, attempt=2, error=RuntimeError("connection reset")) is True
    # Attempt 2 (exhausted retries, attempt counter 3)
    assert manager.should_retry(step, attempt=3, error=RuntimeError("connection reset")) is False


def test_retry_manager_non_retryable_errors():
    """Verify permanent errors (e.g. syntax, schema validation) are not retried."""
    manager = RetryManagerTool()
    step = TaskStep(
        id="s1",
        plugin_name="coding",
        action="execute",
        retry_policy=RetryPolicy(max_retries=3),
    )

    # SyntaxError should not be retried
    assert manager.should_retry(step, attempt=1, error=SyntaxError("invalid syntax")) is False

    # Validation failed should not be retried
    assert manager.should_retry(step, attempt=1, error=ValueError("Input validation failed for payload")) is False

    # Transient error should be retried
    assert manager.should_retry(step, attempt=1, error=TimeoutError("Request timed out")) is True


def test_retry_manager_backoff_calculation():
    """Verify exponential backoff calculation respects initial interval, factor, and ceiling."""
    manager = RetryManagerTool()
    policy = RetryPolicy(
        initial_interval_seconds=1.0,
        backoff_factor=2.0,
        max_interval_seconds=10.0,
    )

    delay1 = manager.get_backoff_delay(policy, attempt=1, jitter=False)
    assert delay1 == 1.0

    delay2 = manager.get_backoff_delay(policy, attempt=2, jitter=False)
    assert delay2 == 2.0

    delay3 = manager.get_backoff_delay(policy, attempt=3, jitter=False)
    assert delay3 == 4.0

    delay5 = manager.get_backoff_delay(policy, attempt=5, jitter=False)
    assert delay5 == 10.0  # Capped at max_interval_seconds


def test_retry_manager_backoff_with_jitter():
    """Verify jitter adds bounded perturbation without exceeding ceiling."""
    manager = RetryManagerTool()
    policy = RetryPolicy(
        initial_interval_seconds=2.0,
        backoff_factor=2.0,
        max_interval_seconds=5.0,
    )

    delay = manager.get_backoff_delay(policy, attempt=1, jitter=True)
    # 2.0 * (1.0 + jitter up to 0.25) -> between 2.0 and 2.5
    assert 2.0 <= delay <= 5.0
