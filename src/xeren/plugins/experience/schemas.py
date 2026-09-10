"""Pydantic schemas and domain models for Xeren Plugin #8: Experience/Feedback Plugin."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ExperienceOperation(str, Enum):
    """Supported operations for the Xeren Experience Plugin."""

    EXPERIENCE_RECORD = "experience_record"
    EXPERIENCE_RETRIEVAL = "experience_retrieval"
    SUCCESS_HISTORY = "success_history"
    FAILURE_HISTORY = "failure_history"
    USER_FEEDBACK = "user_feedback"
    PATTERN_DETECTION = "pattern_detection"
    LESSON_EXTRACTION = "lesson_extraction"
    EXPERIENCE_RANKING = "experience_ranking"
    FAILURE_AVOIDANCE = "failure_avoidance"
    OUTCOME_TRACKING = "outcome_tracking"


class OutcomeType(str, Enum):
    """Outcome category classification."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class UserFeedback(BaseModel):
    """Structured user rating, thumbs-up/down, notes, or corrected outcome."""

    rating: Optional[int] = Field(default=None, ge=1, le=5, description="1-5 star user rating")
    thumbs_up: Optional[bool] = Field(default=None, description="Binary positive/negative feedback")
    comments: Optional[str] = Field(default=None, description="User commentary or guidance")
    corrected_outcome: Optional[str] = Field(default=None, description="User-provided expected output")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp feedback was received",
    )


class FailureWarning(BaseModel):
    """Specific warning derived from past similar failures to avoid repetition."""

    task_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity score to current task")
    failed_action: Optional[str] = Field(default=None, description="Previous action that triggered the failure")
    failed_plugin: Optional[str] = Field(default=None, description="Plugin associated with failure")
    failure_reason: str = Field(..., description="Root cause or error from previous failure")
    avoidance_advice: str = Field(..., description="Constructive action to prevent repeating the mistake")


class LessonItem(BaseModel):
    """Distilled reusable heuristic or rule extracted from experience history."""

    category: str = Field(..., description="Domain or tool category (e.g. 'coding', 'file', 'data')")
    pattern: str = Field(..., description="Observed behavioral or execution pattern")
    lesson: str = Field(..., description="Actionable guideline or best practice")
    supporting_experiences_count: int = Field(
        default=1, ge=1, description="Number of experiences supporting this lesson"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this lesson's validity")


class ExperienceStats(BaseModel):
    """Aggregated outcome metrics across recorded experiences."""

    total_count: int = Field(default=0, ge=0, description="Total recorded experiences")
    success_count: int = Field(default=0, ge=0, description="Successful experiences count")
    failure_count: int = Field(default=0, ge=0, description="Failed experiences count")
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean recorded confidence score")
    plugin_breakdown: Dict[str, int] = Field(
        default_factory=dict, description="Experience count grouped by selected plugin"
    )


class ExperienceItem(BaseModel):
    """Structured record capturing a single execution outcome for memory and learning."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the experience record",
    )
    task: str = Field(..., description="The objective or user instruction attempted")
    context: Optional[str] = Field(default=None, description="Relevant conversational or workspace context")
    selected_plugin: Optional[str] = Field(default=None, description="Name of plugin chosen for execution")
    action: Optional[str] = Field(default=None, description="Specific action, tool, or strategy employed")
    outcome: Any = Field(default=None, description="Observed result, artifact, or response")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    verification_status: Optional[str] = Field(
        default=None, description="Status from VerificationPlugin (e.g. 'verified', 'failed')"
    )
    verification_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Calibrated verification score"
    )
    user_feedback: Optional[UserFeedback] = Field(default=None, description="User ratings or corrections")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall execution confidence")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the execution",
    )
    lesson: Optional[str] = Field(default=None, description="Reusable lesson or takeaway")
    failure_reason: Optional[str] = Field(default=None, description="Diagnosis if execution failed")
    failure_avoidance_advice: Optional[str] = Field(
        default=None, description="Advice to avoid repeating failure"
    )
    error: Optional[str] = Field(default=None, description="Raw error details or exception message")
    is_reusable: bool = Field(
        default=True, description="Whether this experience is verified and safe for positive reuse"
    )
    tags: List[str] = Field(default_factory=list, description="Categorization or search tags")
    content_fingerprint: str = Field(
        default="", description="SHA-256 fingerprint for deduplication"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary execution metadata")

    def generate_fingerprint(self) -> str:
        """Generate a deterministic SHA-256 hash from normalized task, plugin, action, and outcome."""
        outcome_str = ""
        if isinstance(self.outcome, (dict, list)):
            try:
                outcome_str = json.dumps(self.outcome, sort_keys=True)
            except Exception:
                outcome_str = str(self.outcome)
        else:
            outcome_str = str(self.outcome) if self.outcome is not None else ""

        payload = (
            f"{self.task.strip().lower()}|"
            f"{(self.selected_plugin or '').strip().lower()}|"
            f"{(self.action or '').strip().lower()}|"
            f"{outcome_str.strip()[:500]}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ExperienceInput(BaseModel):
    """Input payload for Experience Plugin operations."""

    operation: ExperienceOperation = Field(
        default=ExperienceOperation.EXPERIENCE_RETRIEVAL,
        description="Experience operation to perform",
    )
    item: Optional[ExperienceItem] = Field(
        default=None, description="Complete experience item to record or update"
    )
    experience_id: Optional[str] = Field(
        default=None, description="Specific ID of an experience to look up or attach feedback to"
    )
    task: Optional[str] = Field(
        default=None, description="Task prompt to record or query against"
    )
    context: Optional[str] = Field(default=None, description="Conversational or environment context")
    plugin_name: Optional[str] = Field(default=None, description="Plugin name for filtering or recording")
    action: Optional[str] = Field(default=None, description="Action or tool name")
    outcome: Any = Field(default=None, description="Execution outcome to record")
    success: Optional[bool] = Field(default=None, description="Success flag for recording or filtering")
    verification_status: Optional[str] = Field(default=None, description="Verification outcome")
    verification_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Verification score")
    user_feedback: Optional[UserFeedback] = Field(default=None, description="User feedback to apply")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    lesson: Optional[str] = Field(default=None, description="Reusable lesson or takeaway to record")
    failure_reason: Optional[str] = Field(default=None, description="Diagnosis if execution failed")
    failure_avoidance_advice: Optional[str] = Field(
        default=None, description="Advice to avoid repeating failure"
    )
    error: Optional[str] = Field(default=None, description="Raw error details or exception message")
    limit: int = Field(default=5, ge=1, le=100, description="Maximum number of items to return")
    filter_plugin: Optional[str] = Field(default=None, description="Filter experiences by plugin name")
    tags: List[str] = Field(default_factory=list, description="Filter or categorization tags")
    state: Optional[Dict[str, Any]] = Field(default=None, description="Agent state payload for experience conversion")
    prediction_confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    final_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    split: str = Field(default="train", description="Dataset split")
    verification_passed: bool = Field(default=True)
    verifier: str = Field(default="system")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class ExperienceResult(BaseModel):
    """Result payload produced by Experience Plugin operations."""

    operation: ExperienceOperation = Field(..., description="The operation executed")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    item: Optional[ExperienceItem] = Field(default=None, description="Recorded or modified experience item")
    experiences: List[ExperienceItem] = Field(
        default_factory=list, description="List of matched, retrieved, or ranked experiences"
    )
    failure_warnings: List[FailureWarning] = Field(
        default_factory=list, description="Warnings from past failures relevant to current task"
    )
    lessons: List[LessonItem] = Field(
        default_factory=list, description="Extracted actionable lessons from history"
    )
    stats: Optional[ExperienceStats] = Field(
        default=None, description="Aggregated historical outcome statistics"
    )
    decision_context: Optional[str] = Field(
        default=None, description="Formatted summary of lessons and warnings for agent context"
    )
    error: Optional[str] = Field(default=None, description="Error details if operation failed")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Execution latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")

    model_config = {"arbitrary_types_allowed": True}

    @property
    def record(self) -> Any:
        """Backward-compatible wrapper exposing record.verification.verified."""
        v_passed = True
        score = 1.0
        if self.item is not None:
            if self.item.verification_status == "failed" or self.item.verification_status is False:
                v_passed = False
            elif self.item.verification_status == "verified" or self.item.verification_status is True:
                v_passed = True
            if self.item.verification_score is not None:
                score = float(self.item.verification_score)
        elif self.metadata and "verification_passed" in self.metadata:
            v_passed = bool(self.metadata["verification_passed"])

        class VerificationStub:
            def __init__(self, verified: bool, score: float):
                self.verified = verified
                self.score = score

        class RecordStub:
            def __init__(self, verified: bool, score: float):
                self.verification = VerificationStub(verified, score)

        return RecordStub(v_passed, score)
