"""XerenDispatcher — Routes user queries to plugins automatically using intent detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from xeren.core.intent import IntentClassifier, IntentResult
from xeren.core.session import XerenSession
from xeren.security.schemas import AccessDecision, DataSensitivityTier
from xeren.plugins.manager import PluginManager

logger = logging.getLogger("xeren.core.dispatcher")


@dataclass
class DispatchResponse:
    """Unified response from automated plugin dispatch."""
    query: str
    intent: IntentResult
    plugin_name: str
    success: bool
    data: Any = None
    security_decision: Optional[AccessDecision] = None
    error: Optional[str] = None


class XerenDispatcher:
    """
    Intelligent dispatch orchestrator.

    Takes natural language from the user, classifies intent,
    evaluates security clearance through the 8-layer gate,
    and executes the targeted plugin.
    """

    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        intent_classifier: Optional[IntentClassifier] = None,
        session: Optional[XerenSession] = None,
    ) -> None:
        self.plugin_manager = plugin_manager or PluginManager()
        self.classifier = intent_classifier or IntentClassifier()
        self.session = session or XerenSession()

    def dispatch(self, query: str, context: Optional[Dict[str, Any]] = None) -> DispatchResponse:
        """
        Process user query end-to-end:
        1. Auto-detect intent without user specifying plugin.
        2. Verify security constraints.
        3. Route to target plugin or workspace.
        """
        # 1. Intent Detection
        intent = self.classifier.classify(query, context=context)
        target_plugin = intent.plugin
        logger.info("Auto-dispatched query '%s' to plugin '%s' (conf=%.2f)", query, target_plugin, intent.confidence)

        # 2. Security Check for Sensitive / Automation operations
        security_decision = None
        if target_plugin in ("file", "automation"):
            # Ensure path or operation is allowed
            path_entity = intent.entities.get("path", "active_workspace")
            decision = self.session.gate.check_access(
                path=path_entity,
                operation=intent.action,
                user_id=self.session.user_id,
                user_intent=query,
            )
            security_decision = decision
            if decision.needs_auth:
                return DispatchResponse(
                    query=query,
                    intent=intent,
                    plugin_name=target_plugin,
                    success=False,
                    security_decision=decision,
                    error=f"Authentication required for {decision.tier.value} data.",
                )

        # 3. Execution routing
        try:
            plugin = getattr(self.plugin_manager, "get", getattr(self.plugin_manager, "get_plugin", None))(target_plugin)
            if not plugin:
                # If plugin is not directly registered in PluginManager, handle gracefully
                return DispatchResponse(
                    query=query,
                    intent=intent,
                    plugin_name=target_plugin,
                    success=True,
                    data={"message": f"Routed to {target_plugin} ({intent.action})", "entities": intent.entities},
                )

            # Plugin execution
            result = plugin.execute({"query": query, "intent": intent.action, "entities": intent.entities})
            return DispatchResponse(
                query=query,
                intent=intent,
                plugin_name=target_plugin,
                success=True,
                data=result,
                security_decision=security_decision,
            )

        except Exception as e:
            logger.exception("Error executing plugin %s", target_plugin)
            return DispatchResponse(
                query=query,
                intent=intent,
                plugin_name=target_plugin,
                success=False,
                error=str(e),
                security_decision=security_decision,
            )


__all__ = ["XerenDispatcher", "DispatchResponse"]
