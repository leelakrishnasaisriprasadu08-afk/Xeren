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
