"""
Core contracts every automation plugin implements.

A "plugin" is one self-contained workflow (exam prep, meeting summarizer,
expense report, whatever the user dreams up next). The orchestrator never
needs to know what a plugin does internally -- it only needs three things:

    1. matches(intent)              -> is this the right plugin for this request?
    2. required_permissions(intent) -> what access does it need, and why?
    3. run(context)                 -> do the work, return a result

To add a brand-new automation: write a class implementing these three
methods and register it with the Orchestrator (see main.py for an example).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AutomationContext:
    """Everything a plugin needs to actually do its job."""
    user_text: str
    intent: Dict[str, Any]
    permissions: Dict[str, bool] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def has(self, permission: str) -> bool:
        return self.permissions.get(permission, False)


@dataclass
class AutomationResult:
    """What a plugin hands back once it's done."""
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)


class PermissionRequest:
    """Describes one thing a plugin wants to access, and why -- this is
    what gets shown to the user when the orchestrator asks permission."""

    def __init__(self, key: str, reason: str, required: bool = True):
        self.key = key            # e.g. "local_files", "web_search", "calendar"
        self.reason = reason      # human-readable reason shown to the user
        self.required = required  # if False, the plugin degrades gracefully without it


class Automation(ABC):
    """Base class for every automation/workflow plugin."""

    name: str = "unnamed_automation"
    description: str = "no description provided"

    @abstractmethod
    def matches(self, intent: Dict[str, Any]) -> bool:
        """Return True if this plugin can handle the given parsed intent."""
        raise NotImplementedError

    @abstractmethod
    def required_permissions(self, intent: Dict[str, Any]) -> List[PermissionRequest]:
        """Declare what access this plugin needs for this specific request."""
        raise NotImplementedError

    @abstractmethod
    def run(self, context: AutomationContext) -> AutomationResult:
        """Do the actual work and return a result."""
        raise NotImplementedError
