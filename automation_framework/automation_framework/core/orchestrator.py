"""
Wires everything together, matching the flow described in the brief:

    user text -> understand what they want -> pick the right plugin ->
    ask permission for what that plugin needs -> run it -> hand back a result
"""
from typing import List, Optional

from .base import Automation, AutomationContext, AutomationResult
from .intent_analyzer import IntentAnalyzer
from .llm_client import LLMClient
from .permissions import PermissionManager


class Orchestrator:
    def __init__(
        self,
        plugins: Optional[List[Automation]] = None,
        llm: Optional[LLMClient] = None,
        permission_manager: Optional[PermissionManager] = None,
    ):
        self.llm = llm or LLMClient()
        self.intent_analyzer = IntentAnalyzer(self.llm)
        self.permissions = permission_manager or PermissionManager()
        self.plugins: List[Automation] = plugins or []

    def register(self, plugin: Automation) -> None:
        self.plugins.append(plugin)

    def _select_plugin(self, intent) -> Automation:
        # Prefer a specific plugin over a catch-all one.
        specific = [p for p in self.plugins if p.name != "generic_research" and p.matches(intent)]
        if specific:
            return specific[0]
        catch_all = [p for p in self.plugins if p.matches(intent)]
        if catch_all:
            return catch_all[0]
        raise LookupError("No plugin (not even a fallback) matched this request.")

    def handle(self, user_text: str) -> AutomationResult:
        intent = self.intent_analyzer.analyze(user_text)
        plugin = self._select_plugin(intent)

        print(f"\n[orchestrator] Understood this as a '{plugin.name}' task.")
        needed = plugin.required_permissions(intent)
        granted = self.permissions.request(needed) if needed else {}

        missing_required = [r.key for r in needed if r.required and not granted.get(r.key, False)]
        if missing_required:
            print(
                f"[orchestrator] Missing required access: {', '.join(missing_required)}. "
                f"Continuing with reduced functionality where possible."
            )

        context = AutomationContext(user_text=user_text, intent=intent, permissions=granted)
        return plugin.run(context)
