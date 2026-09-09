"""Pydantic schemas and domain models for Xeren Plugin #7: Verification Plugin."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Calibrated status of a verification operation."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILED = "failed"
    UNVERIFIABLE = "unverifiable"


class VerificationOperation(str, Enum):
    """Supported operations for the Xeren Verification Plugin."""

    OUTPUT_VALIDATION = "output_validation"
    FACT_CHECKING = "fact_checking"
    RESULT_RERANKING = "result_reranking"
    CONSISTENCY_CHECKING = "consistency_checking"
    CODE_VERIFICATION = "code_verification"
    DATA_VERIFICATION = "data_verification"
    SOURCE_EVIDENCE_CHECK = "source_evidence_check"
    CONFIDENCE_SCORING = "confidence_scoring"
    LLM_JUDGE = "llm_judge"
    FINAL_RESPONSE_VERIFICATION = "final_response_verification"


class EvidenceItem(BaseModel):
    """Ground truth, source document, or citation reference used to verify a candidate."""

    source_id: str = Field(..., description="Unique identifier of the evidence source")
    content: str = Field(..., description="Text content or excerpt of the evidence")
    uri: Optional[str] = Field(default=None, description="Optional URI, URL, or filepath")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with evidence")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Source trust or relevance confidence")


class CandidateItem(BaseModel):
    """An alternative output candidate or result item for scoring and reranking."""

    id: str = Field(..., description="Unique identifier of the candidate")
    content: Any = Field(..., description="Candidate payload or text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Candidate-associated metadata")
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Evaluated score of the candidate")


class CheckResult(BaseModel):
    """Result of an individual deterministic or heuristic verification check."""

    name: str = Field(..., description="Name or identifier of the check")
    passed: bool = Field(..., description="Whether the check passed")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Normalized score [0.0, 1.0]")
    reason: Optional[str] = Field(default=None, description="Explanation or diagnostic message")
    actionable_correction: Optional[str] = Field(default=None, description="Suggested fix or correction")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional structured diagnostic details")


class JudgeVerdict(BaseModel):
    """Evaluation verdict produced by an LLM or expert judge."""

    is_valid: bool = Field(..., description="Whether the judged response meets criteria")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Calibrated judgment score [0.0, 1.0]")
    rationale: str = Field(..., description="Detailed explanation for the verdict")
    criteria_scores: Dict[str, float] = Field(default_factory=dict, description="Component scores per rubric criterion")
    suggested_improvements: List[str] = Field(default_factory=list, description="Concrete suggestions for improvement")


class VerificationInput(BaseModel):
    """Input payload for Verification Plugin operations."""

    operation: VerificationOperation = Field(
        default=VerificationOperation.FINAL_RESPONSE_VERIFICATION,
        description="Verification operation to perform",
    )
    candidate: Any = Field(default=None, description="Primary candidate output or response to verify")
    task: Optional[str] = Field(default=None, description="Original task prompt or user request")
    context: Optional[str] = Field(default=None, description="Conversational or execution context")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Ground truth or source evidence items")
    candidates: List[CandidateItem] = Field(default_factory=list, description="Alternative candidates for reranking")
    schema_definition: Optional[Dict[str, Any]] = Field(
        default=None, description="Expected JSON schema or type structure"
    )
    expected_format: Optional[str] = Field(
        default=None, description="Expected format descriptor (e.g. 'json', 'markdown', 'python', 'sql')"
    )
    trajectory: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Reasoning/execution step trajectory for consistency analysis"
    )
    strict_mode: bool = Field(default=False, description="Whether failures trigger strict rejection")
    rubric: Optional[Dict[str, Any]] = Field(default=None, description="Evaluation rubric guidelines for judge")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Threshold for VERIFIED status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class VerificationResult(BaseModel):
    """Result payload produced by Verification Plugin operations."""

    status: VerificationStatus = Field(..., description="Overall verification outcome status")
    operation: VerificationOperation = Field(..., description="The verification operation performed")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Calibrated confidence score [0.0, 1.0]")
    checks: List[CheckResult] = Field(default_factory=list, description="Individual verification checks executed")
    judge_verdict: Optional[JudgeVerdict] = Field(default=None, description="Verdict from LLM or rule-based judge")
    reranked_candidates: Optional[List[CandidateItem]] = Field(
        default=None, description="Reranked candidate items if reranking was performed"
    )
    failure_reasons: List[str] = Field(default_factory=list, description="List of reasons for any failures")
    actionable_corrections: List[str] = Field(
        default_factory=list, description="Concrete suggestions or actions to fix failures"
    )
    evidence_grounding_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Evidence grounding coverage score"
    )
    consistency_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Internal and trajectory consistency score"
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Source provenance details and citations"
    )
    latency_ms: float = Field(default=0.0, ge=0.0, description="Elapsed execution time in milliseconds")
    raw_details: Dict[str, Any] = Field(default_factory=dict, description="Low-level diagnostic details")
