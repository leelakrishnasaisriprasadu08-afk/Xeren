"""Schema definitions for Xeren agent training and experience data."""

from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from xeren.eval.types import EvalSample
from xeren.rag.document import DocumentChunk
from xeren.rag.retrieval.types import SearchResult


class DatasetSplit(str, Enum):
    """Dataset partition splits."""
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


class RetrievalItem(BaseModel):
    """A retrieved context item tagged as useful or irrelevant."""
    source_id: str = Field(..., description="Document or chunk ID")
    content: str = Field(..., description="Retrieved passage text")
    is_useful: bool = Field(..., description="True if useful context, False if irrelevant/distractor")
    relevance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Similarity or relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags")


class ActionStep(BaseModel):
    """A single action execution step in an agent trajectory."""
    step_index: int = Field(..., ge=0, description="0-indexed execution step")
    plan_step: str = Field(..., description="Plan objective corresponding to this action")
    tool_name: str = Field(..., description="Selected tool name or action type")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to the tool")
    action_selection_rationale: Optional[str] = Field(default=None, description="Reasoning behind selecting this tool/action")
    result: str = Field(..., description="Observation or execution result")
    success: bool = Field(default=True, description="Whether the tool execution succeeded")
    error_message: Optional[str] = Field(default=None, description="Error detail if execution failed")
    correction: Optional[str] = Field(default=None, description="Correction or recovery applied after failure")


class AlternativeCandidate(BaseModel):
    """Alternative candidate action or plan evaluated during decision making."""
    candidate_action: str = Field(..., description="Alternative action/plan description")
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Predicted score for this alternative")
    comparison_note: str = Field(..., description="Comparative analysis versus selected action")
    rejected_reason: str = Field(..., description="Why this alternative was rejected")


class VerificationDetails(BaseModel):
    """Outcome verification results."""
    verified: bool = Field(..., description="Whether verification passed")
    verifier: str = Field(..., description="Verifier type (e.g. human, unit_test, rule_verifier, llm_judge)")
    score: float = Field(..., ge=0.0, le=1.0, description="Verification confidence score in [0.0, 1.0]")
    details: Dict[str, Any] = Field(default_factory=dict, description="Verification checks or notes")


class ExperienceRecord(BaseModel):
    """A complete agent trajectory experience record for training/learning."""
    sample_id: str = Field(..., description="Unique record identifier")
    task: str = Field(..., description="Goal or instruction assigned to the agent")
    plan: List[str] = Field(default_factory=list, description="Planned step sequence")
    actions: List[ActionStep] = Field(default_factory=list, description="Executed actions with results")
    prediction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence/probability of the prediction")
    verification: VerificationDetails = Field(..., description="Verification result")
    alternatives: List[AlternativeCandidate] = Field(default_factory=list, description="Alternative comparisons")
    retrieval_items: List[RetrievalItem] = Field(default_factory=list, description="Useful and irrelevant retrievals")
    success: bool = Field(..., description="Overall task success or failure")
    failure_reason: Optional[str] = Field(default=None, description="Reason if task failed")
    recovery_strategy: Optional[str] = Field(default=None, description="Recovery/adaptation strategy employed")
    final_quality_score: float = Field(..., ge=0.0, le=1.0, description="Final outcome/quality score in [0.0, 1.0]")
    split: DatasetSplit = Field(default=DatasetSplit.TRAIN, description="Data split")
    is_verified: bool = Field(default=False, description="Whether example is human/rule verified")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional environment/model metadata")

    def content_fingerprint(self) -> str:
        """Generate a SHA-256 fingerprint from task and normalized action trajectory."""
        action_repr = [
            f"{a.step_index}:{a.tool_name}:{json.dumps(a.tool_args, sort_keys=True)}:{a.result}"
            for a in self.actions
        ]
        payload = f"{self.task.strip()}|{'|'.join(action_repr)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_eval_sample(self) -> EvalSample:
        """Convert experience record to Xeren EvalSample for evaluation framework integration."""
        retrieved_chunks = [
            SearchResult(
                chunk=DocumentChunk(
                    chunk_id=item.source_id,
                    document_id=item.source_id.split("#")[0],
                    content=item.content,
                    chunk_index=i,
                ),
                score=item.relevance_score or (1.0 if item.is_useful else 0.0),
            )
            for i, item in enumerate(self.retrieval_items)
        ]
        last_action_result = self.actions[-1].result if self.actions else ""
        expected_ids = [item.source_id for item in self.retrieval_items if item.is_useful]

        return EvalSample(
            sample_id=self.sample_id,
            query=self.task,
            ground_truth_answer=None,
            expected_source_ids=expected_ids,
            retrieved_chunks=retrieved_chunks,
            generated_answer=last_action_result,
            metadata={
                "prediction_confidence": self.prediction_confidence,
                "final_quality_score": self.final_quality_score,
                "success": self.success,
                "split": self.split.value,
                "is_verified": self.is_verified,
                **self.metadata,
            },
        )
