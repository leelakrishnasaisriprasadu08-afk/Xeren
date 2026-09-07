"""Tests for DefaultPermissionManager authorization and approval gates."""

import pytest

from xeren.agent.actions import Action, PermissionLevel
from xeren.agent.permissions import DefaultPermissionManager


def test_safe_action_automatically_authorized():
    """Verify standard safe actions are authorized without user intervention."""
    pm = DefaultPermissionManager()
    action = Action(target="research", parameters={"query": "python tips"})

    assert pm.get_permission_level(action) == PermissionLevel.SAFE
    assert pm.is_authorized(action) is True
    assert pm.request_approval(action) is True


def test_consequential_keywords_require_approval():
    """Verify actions with consequential keywords trigger approval requirement."""
    pm = DefaultPermissionManager()

    publish_act = Action(target="website", parameters={"operation": "publish_site"})
    assert pm.get_permission_level(publish_act) == PermissionLevel.REQUIRES_APPROVAL
    assert pm.is_authorized(publish_act) is False

    pay_act = Action(target="browser", parameters={"action": "click", "url": "https://pay.com"})
    assert pm.get_permission_level(pay_act) == PermissionLevel.REQUIRES_APPROVAL

    delete_act = Action(target="data", parameters={"operation": "delete_dataset"})
    assert pm.get_permission_level(delete_act) == PermissionLevel.REQUIRES_APPROVAL


def test_approval_callback_granted_and_denied():
    """Verify injected approval callback controls authorization."""
    approved_actions = {"act-allowed"}

    def mock_callback(action: Action, ctx):
        return action.action_id in approved_actions

    pm = DefaultPermissionManager(approval_callback=mock_callback)

    act_allowed = Action(action_id="act-allowed", target="browser", parameters={"action": "upload", "file_path": "x"})
    act_denied = Action(action_id="act-denied", target="browser", parameters={"action": "upload", "file_path": "y"})

    assert pm.request_approval(act_allowed) is True
    assert pm.is_authorized(act_allowed) is True

    assert pm.request_approval(act_denied) is False
    assert pm.is_authorized(act_denied) is False


def test_manual_approval_and_revocation():
    """Verify explicit approve and revoke programmatic hooks."""
    pm = DefaultPermissionManager()
    action = Action(
        action_id="manual-1",
        target="website",
        permission_level=PermissionLevel.REQUIRES_APPROVAL,
    )

    assert pm.is_authorized(action) is False

    pm.approve("manual-1")
    assert pm.is_authorized(action) is True

    pm.revoke("manual-1")
    assert pm.is_authorized(action) is False
