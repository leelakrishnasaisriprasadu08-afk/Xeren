"""Permission management and approval workflow for the Autonomous Work Agent."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from xeren.agent.actions import Action, PermissionLevel
from xeren.agent.interfaces import PermissionManager

logger = logging.getLogger("xeren.agent.permissions")


# Default sensitive / consequential trigger terms
CONSEQUENTIAL_KEYWORDS = {
    "publish",
    "send_message",
    "email",
    "pay",
    "payment",
    "purchase",
    "checkout",
    "order",
    "delete",
    "destroy",
    "drop_table",
    "external_submit",
    "account_modify",
    "transfer",
}


class DefaultPermissionManager(PermissionManager):
    """Enforces authorization boundaries and approval workflows for agent actions."""

    def __init__(
        self,
        approval_callback: Optional[Callable[[Action, Optional[Dict[str, Any]]], bool]] = None,
        custom_consequential_keywords: Optional[List[str]] = None,
        auto_approve_safe_only: bool = True,
    ) -> None:
        self.approval_callback = approval_callback
        self.consequential_keywords = set(CONSEQUENTIAL_KEYWORDS)
        if custom_consequential_keywords:
            self.consequential_keywords.update(k.lower() for k in custom_consequential_keywords)
        self.auto_approve_safe_only = auto_approve_safe_only

        # Set of explicitly approved action_ids
        self._approved_action_ids: Set[str] = set()

    def get_permission_level(self, action: Action) -> PermissionLevel:
        """Evaluate action properties to determine if approval is required."""
        # 1. Explicitly declared permission level
        if action.permission_level == PermissionLevel.REQUIRES_APPROVAL:
            return PermissionLevel.REQUIRES_APPROVAL

        # 2. Inspect target, operation, description, and parameter values
        target = action.target.lower()
        params = action.parameters
        operation = str(params.get("operation", "")).lower()
        desc = (action.description or "").lower()
        param_values = " ".join(str(v) for v in params.values()).lower()

        # Check against consequential operations and keywords
        search_terms = f"{target} {operation} {desc} {param_values}"
        for keyword in self.consequential_keywords:
            if keyword in search_terms:
                logger.info(
                    "Action '%s' classified as REQUIRES_APPROVAL due to keyword '%s'",
                    action.action_id,
                    keyword,
                )
                return PermissionLevel.REQUIRES_APPROVAL

        # Consequential browser actions (e.g. form submission, purchase, external posts)
        if target == "browser":
            browser_action = str(params.get("action", "")).lower()
            if browser_action in {"upload", "submit"}:
                return PermissionLevel.REQUIRES_APPROVAL
            url = str(params.get("url", "")).lower()
            if any(k in url for k in ["payment", "checkout", "login", "auth"]):
                return PermissionLevel.REQUIRES_APPROVAL

        return PermissionLevel.SAFE

    def is_authorized(self, action: Action, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check whether the action is permitted to execute."""
        level = self.get_permission_level(action)
        if level == PermissionLevel.SAFE:
            return True

        # Check if this specific action has been explicitly approved
        return action.action_id in self._approved_action_ids

    def request_approval(self, action: Action, context: Optional[Dict[str, Any]] = None) -> bool:
        """Request authorization for a consequential action via the injected callback."""
        level = self.get_permission_level(action)
        if level == PermissionLevel.SAFE:
            return True

        if action.action_id in self._approved_action_ids:
            return True

        if self.approval_callback is not None:
            approved = self.approval_callback(action, context)
            if approved:
                self._approved_action_ids.add(action.action_id)
                logger.info("Approval granted for action '%s'", action.action_id)
                return True
            logger.warning("Approval denied for action '%s'", action.action_id)
            return False

        logger.warning(
            "Action '%s' requires approval but no approval callback was configured. Authorization denied.",
            action.action_id,
        )
        return False

    def approve(self, action_id: str) -> None:
        """Manually grant explicit approval for an action ID."""
        self._approved_action_ids.add(action_id)
        logger.info("Explicit approval added for action '%s'", action_id)

    def revoke(self, action_id: str) -> None:
        """Revoke authorization for an action ID."""
        self._approved_action_ids.discard(action_id)

    def clear(self) -> None:
        """Clear all approved action IDs."""
        self._approved_action_ids.clear()


__all__ = ["DefaultPermissionManager"]
