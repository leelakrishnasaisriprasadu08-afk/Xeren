"""Tests for PermissionManager evaluating risk categories and approval workflows."""

import pytest

from xeren.agent.permissions import PermissionManager, PermissionMode
from xeren.agent.types import ActionCategory, AgentAction


def test_permission_classification():
    """Verify actions are correctly categorized into risk levels."""
    pm = PermissionManager()

    obs_action = AgentAction(action_type="observe")
    assert pm.classify_action(obs_action) == ActionCategory.READ_ONLY
    assert not pm.is_consequential(obs_action)

    click_action = AgentAction(action_type="click", target="#button")
    assert pm.classify_action(click_action) == ActionCategory.INTERACTIVE
    assert not pm.is_consequential(click_action)

    upload_action = AgentAction(action_type="upload", target="#file")
    assert pm.classify_action(upload_action) == ActionCategory.CONSEQUENTIAL
    assert pm.is_consequential(upload_action)

    download_action = AgentAction(action_type="download")
    assert pm.classify_action(download_action) == ActionCategory.CONSEQUENTIAL

    custom_consequential = AgentAction(action_type="custom", consequential=True)
    assert pm.is_consequential(custom_consequential)


def test_auto_approve_allows_safe_blocks_consequential():
    """Verify auto-approve mode permits safe actions and queues consequential ones."""
    pm = PermissionManager(mode=PermissionMode.AUTO_APPROVE, require_consequential_approval=True)

    safe_action = AgentAction(action_type="click", target="#btn")
    allowed, reason = pm.check_permission(safe_action)
    assert allowed is True
    assert reason is None

    consequential = AgentAction(action_type="upload", target="#file")
    allowed, reason = pm.check_permission(consequential)
    assert allowed is False
    assert "requires user approval" in (reason or "")
    assert consequential.action_id in pm.list_pending()


def test_grant_and_deny_approvals():
    """Verify granting and denying approvals alters execution permission."""
    pm = PermissionManager()
    action = AgentAction(action_type="download")

    # Initial check fails and queues
    allowed, _ = pm.check_permission(action)
    assert allowed is False
    assert action.action_id in pm.list_pending()

    # Grant approval
    pm.grant_approval(action.action_id)
    assert action.action_id not in pm.list_pending()

    # Subsequent check allows
    allowed_now, reason = pm.check_permission(action)
    assert allowed_now is True
    assert reason is None

    # Deny another action
    denied_action = AgentAction(action_type="upload")
    pm.check_permission(denied_action)
    pm.deny_approval(denied_action.action_id, reason="Policy restricts file uploads")

    allowed_denied, reason_denied = pm.check_permission(denied_action)
    assert allowed_denied is False
    assert "denied" in (reason_denied or "").lower()


def test_strict_mode_blocks_interactive_actions():
    """Verify strict mode requires approval for interactive actions like click or type."""
    pm = PermissionManager(mode=PermissionMode.STRICT)

    interactive = AgentAction(action_type="click", target="#link")
    allowed, reason = pm.check_permission(interactive)
    assert allowed is False
    assert "strict mode" in (reason or "").lower()
