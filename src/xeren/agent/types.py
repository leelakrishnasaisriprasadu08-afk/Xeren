"""Core data models and type schemas for the Xeren Autonomous Work Agent."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
from pydantic import BaseModel, Field


class BrowserActionType(str, Enum):
    """Supported browser action types."""

    NAVIGATE = "navigate"
    OBSERVE = "observe"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    EXTRACT = "extract"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    CLOSE = "close"
    WAIT = "wait"


class AgentStatus(str, Enum):
    """Lifecycle status of the agent."""

    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    RECOVERING = "recovering"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionCategory(str, Enum):
    """Risk/permission classification for agent actions."""

    READ_ONLY = "read_only"
    INTERACTIVE = "interactive"
    CONSEQUENTIAL = "consequential"
    SYSTEM = "system"


class BrowserError(BaseModel):
    """Structured browser error payload."""

    code: str = Field(..., description="Machine-readable error code (e.g. TIMEOUT, NOT_FOUND)")
    message: str = Field(..., description="Safe, sanitized error description")
    category: str = Field(default="browser_error", description="Error category classification")
    selector: Optional[str] = Field(default=None, description="Selector that triggered the failure if applicable")
    url: Optional[str] = Field(default=None, description="Current page URL during failure")
    recoverable: bool = Field(default=True, description="Whether RecoveryManager can attempt recovery/retry")
    details: Dict[str, Any] = Field(default_factory=dict, description="Safe diagnostic metadata without credentials")


class InteractiveElement(BaseModel):
    """Interactive DOM element representation."""

    element_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Element identifier")
    tag_name: str = Field(..., description="HTML tag name (e.g. button, input, a)")
    selector: str = Field(..., description="Unique CSS or XPath selector")
    text: Optional[str] = Field(default=None, description="Visible inner text")
    element_type: Optional[str] = Field(default=None, description="Input type attribute if applicable")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Sanitized element attributes")
    is_visible: bool = Field(default=True, description="Whether element is visible in viewport")
    is_enabled: bool = Field(default=True, description="Whether element can be interacted with")
    bounding_box: Optional[Dict[str, float]] = Field(default=None, description="x, y, width, height")


class BrowserObservation(BaseModel):
    """Structured extraction and state snapshot of a browser page."""

    url: str = Field(default="", description="Active page URL")
    title: str = Field(default="", description="Page title")
    text_content: str = Field(default="", description="Sanitized text content extracted from page")
    interactive_elements: List[InteractiveElement] = Field(
        default_factory=list, description="Discoverable interactive elements"
    )
    forms: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted form elements and fields")
    links: List[Dict[str, str]] = Field(default_factory=list, description="Anchor links (text, href)")
    scroll_position: Dict[str, int] = Field(
        default_factory=lambda: {"x": 0, "y": 0}, description="Current scroll coordinate"
    )
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1280, "height": 800}, description="Viewport dimensions"
    )
    status_code: Optional[int] = Field(default=200, description="HTTP status code if known")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Capture timestamp"
    )
    error: Optional[BrowserError] = Field(default=None, description="Error encountered during observation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Observation metadata")


class AgentAction(BaseModel):
    """Action proposed or executed by an autonomous agent."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique action identifier")
    action_type: str = Field(..., description="Action name or tool type (e.g. navigate, click, type)")
    target: Optional[str] = Field(default=None, description="Target selector, URL, or identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to the action")
    requires_approval: bool = Field(default=False, description="True if action requires user confirmation")
    consequential: bool = Field(default=False, description="True if action causes external side-effects")
    description: Optional[str] = Field(default=None, description="Human-readable description of the action intent")
    category: ActionCategory = Field(default=ActionCategory.INTERACTIVE, description="Permission risk category")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Action tracing metadata")


class ActionResult(BaseModel):
    """Execution outcome of an AgentAction."""

    action_id: str = Field(..., description="Corresponding AgentAction id")
    success: bool = Field(..., description="Whether action succeeded")
    data: Optional[Any] = Field(default=None, description="Structured execution payload")
    output: Optional[Any] = Field(default=None, description="Structured execution output or response payload")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Artifacts produced during execution")
    error: Optional[str] = Field(default=None, description="Sanitized error message if failed")
    error_category: Optional[str] = Field(default=None, description="Error category classification")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    observation: Optional[BrowserObservation] = Field(
        default=None, description="Post-action page observation if applicable"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        if self.output is None and self.data is not None:
            self.output = self.data
        elif self.data is None and self.output is not None:
            self.data = self.output


class AgentState(BaseModel):
    """State trace and memory of an autonomous work agent."""

    state_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Snapshot identifier")
    session_id: Optional[str] = Field(default=None, description="Optional session identifier")
    task: str = Field(..., description="Top-level user objective or goal")
    step_count: int = Field(default=0, ge=0, description="Total executed steps")
    plan: List[str] = Field(default_factory=list, description="Current sequence of planned steps")
    current_step: Optional[str] = Field(default=None, description="Currently active plan step")
    history: List[Tuple[AgentAction, ActionResult]] = Field(
        default_factory=list, description="Execution history trace"
    )
    last_observation: Optional[BrowserObservation] = Field(
        default=None, description="Latest page or environment observation"
    )
    memory: Dict[str, Any] = Field(default_factory=dict, description="Key-value agent memory store")
    task_plan: Optional[Any] = Field(default=None, description="Structured TaskPlan object if using CorePlanner")
    status: AgentStatus = Field(default=AgentStatus.INITIALIZING, description="Current agent execution status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    model_config = {"arbitrary_types_allowed": True}
