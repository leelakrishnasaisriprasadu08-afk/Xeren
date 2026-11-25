"""Action and ActionResult schemas for the Xeren Autonomous Work Agent."""

from enum import Enum
import hashlib
import json
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission levels for action authorization."""

    SAFE = "safe"
    REQUIRES_APPROVAL = "requires_approval"


class ActionType(str, Enum):
    """Enumeration of high-level action categories."""

    PLUGIN = "plugin"
    BROWSER = "browser"
    VERIFICATION = "verification"
    SYSTEM = "system"
    CUSTOM = "custom"


class Action(BaseModel):
    """A structured, executable action plan step."""

    action_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the action",
    )
    action_type: str = Field(
        default=ActionType.PLUGIN.value,
        description="Type category of the action (plugin, browser, etc.)",
    )
    target: str = Field(
        ...,
        description="Target plugin, tool, or handler name (e.g. 'coding', 'research', 'browser')",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters or payload passed to the target",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of what this action intends to accomplish",
    )
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.SAFE,
        description="Authorization level required to execute this action",
    )
    timeout_seconds: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Optional timeout limit in seconds for this specific action",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional routing or execution metadata",
    )

    model_config = {"arbitrary_types_allowed": True}

    def fingerprint(self) -> str:
        """Generate a deterministic signature of target and normalized parameters.

        Used for stagnation detection and cycle/loop prevention.
        """
        try:
            param_str = json.dumps(self.parameters, sort_keys=True, default=str)
        except Exception:
            param_str = str(self.parameters)
        payload = f"{self.target}:{self.action_type}:{param_str}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ActionResult(BaseModel):
    """Structured execution result of an action."""

    action_id: str = Field(
        ...,
        description="Identifier of the action that was executed",
    )
    success: bool = Field(
        ...,
        description="Whether the action executed successfully",
    )
    output: Optional[Any] = Field(
        default=None,
        description="Structured execution output or response payload",
    )
    data: Optional[Any] = Field(
        default=None,
        description="Structured execution payload alias",
    )
    error: Optional[str] = Field(
        default=None,
        description="Detailed error message if execution failed",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution duration in milliseconds",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Artifacts produced by this action (e.g. generated files, data tables)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution diagnostic and tracing metadata",
    )

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        if self.output is None and self.data is not None:
            self.output = self.data
        elif self.data is None and self.output is not None:
            self.data = self.output


__all__ = [
    "PermissionLevel",
    "ActionType",
    "Action",
    "ActionResult",
]
