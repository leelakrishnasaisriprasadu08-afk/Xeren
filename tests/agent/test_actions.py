"""Tests for Action, ActionResult, and PermissionLevel models."""

import pytest
from pydantic import ValidationError

from xeren.agent.actions import Action, ActionResult, ActionType, PermissionLevel


def test_action_creation_and_defaults():
    """Verify Action default parameters and field population."""
    action = Action(target="coding", parameters={"task": "write tests"})
    assert action.action_id is not None
    assert action.action_type == ActionType.PLUGIN.value
    assert action.target == "coding"
    assert action.permission_level == PermissionLevel.SAFE
    assert action.timeout_seconds is None


def test_action_fingerprint():
    """Verify deterministic action fingerprinting for stagnation detection."""
    act1 = Action(action_id="1", target="coding", parameters={"a": 1, "b": 2})
    act2 = Action(action_id="2", target="coding", parameters={"b": 2, "a": 1})
    act3 = Action(action_id="3", target="research", parameters={"a": 1, "b": 2})

    # Order of dict keys shouldn't change the normalized fingerprint
    assert act1.fingerprint() == act2.fingerprint()
    # Different target produces different fingerprint
    assert act1.fingerprint() != act3.fingerprint()


def test_action_result_creation():
    """Verify ActionResult creation and attributes."""
    res = ActionResult(
        action_id="act-123",
        success=True,
        output={"status": "ok"},
        latency_ms=15.4,
        artifacts={"chart": "plot.png"},
    )
    assert res.action_id == "act-123"
    assert res.success is True
    assert res.output == {"status": "ok"}
    assert res.latency_ms == 15.4
    assert res.artifacts == {"chart": "plot.png"}


def test_malformed_action_validation():
    """Verify pydantic validation raises error on malformed action definition."""
    with pytest.raises(ValidationError):
        # Target is required
        Action.model_validate({"parameters": {}})  # type: ignore

    with pytest.raises(ValidationError):
        # Invalid permission level enum
        Action.model_validate({"target": "coding", "permission_level": "INVALID_PERMISSION"})
