"""ExperiencePlugin converting TaskState to canonical ExperienceRecord and persisting to ExperienceDataset."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Type, Union
import uuid

from pydantic import BaseModel, Field

from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    VerificationDetails,
)
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)

logger = logging.getLogger("xeren.agent.plugins.experience")


# ─────────────────────────────────────────────────────────────────────────────
# Input / Output schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExperienceInput(BaseModel):
    """Input payload for experience recording supporting both state snapshots and explicit records."""

    record: Optional[ExperienceRecord] = Field(default=None, description="Explicit ExperienceRecord to store")
    state: Optional[Dict[str, Any]] = Field(default=None, description="AgentState dictionary or serialized data")
    task: Optional[str] = Field(default=None, description="Task or goal description")
    task_id: Optional[str] = Field(default=None, description="Unique task identifier")
    goal: Optional[str] = Field(default=None, description="Goal prompt")
    status: Optional[str] = Field(default=None, description="Execution status")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Executed steps")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Artifacts dictionary")
    prediction_confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    final_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    split: str = Field(default="train", description="Target dataset split")
    verification_passed: bool = Field(default=True)
    verification_status: Optional[str] = Field(default=None)
    verification_score: Optional[float] = Field(default=None)
    verifier: str = Field(default="system")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"arbitrary_types_allowed": True}


class ExperienceOutput(BaseModel):
    """Output summary of experience recording delivering canonical ExperienceRecord."""

    record: Optional[ExperienceRecord] = Field(default=None, description="Constructed ExperienceRecord")
    fingerprint: str = Field(default="", description="Content hash fingerprint")
    success: bool = Field(default=True, description="Whether record was stored successfully")
    stored: bool = Field(default=True, description="Stored flag")
    record_id: str = Field(default="", description="Recorded sample or record id")
    sample_id: str = Field(default="", description="Sample identifier")
    total_records: int = Field(default=0, description="Total count of records in dataset")
    message: str = Field(default="", description="Status message")

    model_config = {"arbitrary_types_allowed": True}


# ─────────────────────────────────────────────────────────────────────────────
# Plugin
# ─────────────────────────────────────────────────────────────────────────────

class ExperiencePlugin(BasePlugin):
    """Modular plugin that captures agent trajectories into canonical ExperienceRecord and ExperienceDataset."""

    def __init__(self, dataset: Optional[ExperienceDataset] = None, **kwargs: Any) -> None:
        self.dataset = dataset if dataset is not None else ExperienceDataset()

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="experience",
            version="0.1.0",
            description="Transforms agent trajectory executions into verified ExperienceRecord datasets",
            capabilities=[
                PluginCapability.EXPERIENCE_RECORD,
                PluginCapability.SUCCESS_HISTORY,
                PluginCapability.FAILURE_HISTORY,
                PluginCapability.OUTCOME_TRACKING,
            ],
            input_schema_name="ExperienceInput",
            output_schema_name="ExperienceOutput",
            author="Xeren",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ExperienceInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ExperienceOutput

    def record_task_state(
        self,
        state: Any,
        verification: Optional[Any] = None,
        prediction_confidence: float = 1.0,
    ) -> ExperienceRecord:
        """Convert a TaskState or AgentState trajectory into an ExperienceRecord and store in dataset."""
        task_id = getattr(state, "task_id", getattr(state, "state_id", str(uuid.uuid4())))
        goal = getattr(state, "goal", getattr(state, "task", "Autonomous Task"))
        status_val = getattr(getattr(state, "status", None), "value", str(getattr(state, "status", "completed")))
        is_success = status_val in ("completed", "success")

        action_steps: List[ActionStep] = []
        step_idx = 0

        # Handle TaskState completed_steps & failed_steps
        completed_steps = getattr(state, "completed_steps", []) or []
        failed_steps = getattr(state, "failed_steps", []) or []

        for res in completed_steps:
            target_name = (res.metadata or {}).get("target", (res.metadata or {}).get("plugin_name", "unknown"))
            action_steps.append(
                ActionStep(
                    step_index=step_idx,
                    plan_step=f"Step {step_idx}: Execute {target_name}",
                    tool_name=target_name,
                    tool_args=res.metadata or {},
                    result=str(res.output) if getattr(res, "output", None) is not None else (str(res.data) if getattr(res, "data", None) is not None else "success"),
                    success=res.success,
                    error_message=res.error,
                )
            )
            step_idx += 1

        for res in failed_steps:
            target_name = (res.metadata or {}).get("target", (res.metadata or {}).get("plugin_name", "unknown"))
            action_steps.append(
                ActionStep(
                    step_index=step_idx,
                    plan_step=f"Step {step_idx}: Execute {target_name} (failed)",
                    tool_name=target_name,
                    tool_args=res.metadata or {},
                    result="failed",
                    success=False,
                    error_message=res.error,
                )
            )
            step_idx += 1

        # Handle AgentState history (tuples of (AgentAction, ActionResult))
        history = getattr(state, "history", []) or []
        if not action_steps and history:
            for item in history:
                if isinstance(item, (tuple, list)) and len(item) == 2:
                    act, res = item
                    act_dict = act if isinstance(act, dict) else act.model_dump()
                    res_dict = res if isinstance(res, dict) else res.model_dump()
                elif isinstance(item, dict):
                    act_dict = item.get("action", {})
                    res_dict = item.get("result", {})
                else:
                    continue

                action_steps.append(
                    ActionStep(
                        step_index=step_idx,
                        plan_step=act_dict.get("description") or f"Step {step_idx}",
                        tool_name=act_dict.get("action_type", "action"),
                        tool_args=act_dict.get("parameters", {}),
                        result=str(res_dict.get("data") or res_dict.get("error") or "Success"),
                        success=res_dict.get("success", True),
                        error_message=res_dict.get("error"),
                    )
                )
                step_idx += 1

        # Plan extraction
        plan_list: List[str] = []
        if hasattr(state, "plan") and state.plan:
            plan_list = [
                (getattr(p, "description", None) or getattr(p, "target", None) or str(p))
                if not isinstance(p, str)
                else p
                for p in state.plan
            ]
        elif hasattr(state, "remaining_steps"):
            plan_list = [
                getattr(a, "description", None) or f"{getattr(a, 'action_type', 'action')}:{getattr(a, 'target', '')}"
                for a in state.remaining_steps
            ]
        if not plan_list and action_steps:
            plan_list = [s.plan_step for s in action_steps]

        # Verification conversion
        if isinstance(verification, VerificationDetails):
            verif = verification
        elif hasattr(verification, "to_verification_details"):
            verif = verification.to_verification_details()
        elif verification and isinstance(verification, dict):
            verif = VerificationDetails(
                verified=bool(verification.get("verified", is_success)),
                verifier=str(verification.get("verifier", "verifier")),
                score=float(verification.get("score", 1.0 if is_success else 0.0)),
                details=verification.get("details", {}),
            )
        else:
            verif = VerificationDetails(
                verified=is_success,
                verifier="task_evaluator",
                score=1.0 if is_success else 0.0,
                details={"status": status_val, "completed_steps": len(completed_steps)},
            )

        failure_reason = None
        if not is_success:
            if failed_steps and failed_steps[-1].error:
                failure_reason = failed_steps[-1].error
            elif hasattr(state, "metadata") and state.metadata.get("failure_reason"):
                failure_reason = state.metadata["failure_reason"]
            else:
                failure_reason = f"Task terminated with status: {status_val}"

        recovery_strategy = getattr(state, "metadata", {}).get("recovery_strategy")

        record = ExperienceRecord(
            sample_id=str(task_id),
            task=str(goal),
            plan=plan_list,
            actions=action_steps,
            prediction_confidence=prediction_confidence,
            verification=verif,
            success=is_success,
            failure_reason=failure_reason,
            recovery_strategy=recovery_strategy,
            final_quality_score=verif.score if is_success else 0.0,
            split=DatasetSplit.TRAIN,
            is_verified=verif.verified,
            metadata={
                "task_id": str(task_id),
                "status": status_val,
                **(getattr(state, "metadata", {}) or {}),
            },
        )

        self.dataset.add(record, enforce_verified=False)
        return record

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Execute experience recording operation."""
        start_time = time.perf_counter()
        try:
            validated: ExperienceInput = (
                input_data if isinstance(input_data, ExperienceInput) else self.validate_input(input_data)
            )

            # Case 1: Explicit ExperienceRecord
            if validated.record is not None:
                self.dataset.add(validated.record, enforce_verified=False)
                output = ExperienceOutput(
                    record=validated.record,
                    fingerprint=validated.record.content_fingerprint(),
                    success=True,
                    stored=True,
                    sample_id=validated.record.sample_id,
                    record_id=validated.record.sample_id,
                    total_records=len(self.dataset),
                    message=f"ExperienceRecord {validated.record.sample_id} recorded successfully.",
                )
                return PluginExecutionResult(
                    plugin_name=self.name,
                    success=True,
                    output=output,
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                )

            # Case 2: AgentState dictionary
            if validated.state is not None:
                state_dict = validated.state
                task = state_dict.get("task") or validated.task or validated.goal or "Agent Task"
                task_id = state_dict.get("state_id") or state_dict.get("task_id") or validated.task_id or str(uuid.uuid4())
                history = state_dict.get("history", [])
                plan = state_dict.get("plan", [])

                action_steps: List[ActionStep] = []
                for i, step_item in enumerate(history):
                    if isinstance(step_item, (list, tuple)) and len(step_item) == 2:
                        act, res = step_item
                        act_dict = act if isinstance(act, dict) else act.model_dump()
                        res_dict = res if isinstance(res, dict) else res.model_dump()
                    elif isinstance(step_item, dict):
                        act_dict = step_item.get("action", {})
                        res_dict = step_item.get("result", {})
                    else:
                        continue

                    action_steps.append(
                        ActionStep(
                            step_index=i,
                            plan_step=act_dict.get("description") or f"Step {i}",
                            tool_name=act_dict.get("action_type", "action"),
                            tool_args=act_dict.get("parameters", {}),
                            result=str(res_dict.get("data") or res_dict.get("error") or "Success"),
                            success=res_dict.get("success", True),
                            error_message=res_dict.get("error"),
                        )
                    )

                verification = VerificationDetails(
                    verified=validated.verification_passed,
                    verifier=validated.verifier,
                    score=validated.final_quality_score,
                    details={"step_count": len(action_steps)},
                )

                split_enum = DatasetSplit.TRAIN
                if validated.split in DatasetSplit._value2member_map_:
                    split_enum = DatasetSplit(validated.split)

                record = ExperienceRecord(
                    sample_id=str(task_id),
                    task=str(task),
                    plan=plan if isinstance(plan, list) else [],
                    actions=action_steps,
                    prediction_confidence=validated.prediction_confidence,
                    verification=verification,
                    success=validated.verification_passed,
                    final_quality_score=validated.final_quality_score,
                    split=split_enum,
                    is_verified=validated.verification_passed,
                    metadata={"source": "autonomous_work_agent", **validated.metadata},
                )

                self.dataset.add(record, enforce_verified=False)
                output = ExperienceOutput(
                    record=record,
                    fingerprint=record.content_fingerprint(),
                    success=True,
                    stored=True,
                    sample_id=record.sample_id,
                    record_id=record.sample_id,
                    total_records=len(self.dataset),
                    message=f"Experience for task '{record.task}' recorded.",
                )
                return PluginExecutionResult(
                    plugin_name=self.name,
                    success=True,
                    output=output,
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                )

            # Case 3: Fallback snapshot from task/goal
            task = validated.task or validated.goal or "General Task"
            sample_id = validated.task_id or str(uuid.uuid4())
            record = ExperienceRecord(
                sample_id=sample_id,
                task=task,
                verification=VerificationDetails(verified=validated.verification_passed, score=validated.final_quality_score),
                success=validated.verification_passed,
                is_verified=validated.verification_passed,
                final_quality_score=validated.final_quality_score,
                split=DatasetSplit.TRAIN,
            )
            self.dataset.add(record, enforce_verified=False)
            output = ExperienceOutput(
                record=record,
                fingerprint=record.content_fingerprint(),
                success=True,
                stored=True,
                sample_id=sample_id,
                record_id=sample_id,
                total_records=len(self.dataset),
                message=f"Task {sample_id} recorded.",
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=output,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        except Exception as err:
            logger.error("[ExperiencePlugin] execute failed: %s", err)
            return PluginExecutionResult(
                plugin_name=self.name,
                success=False,
                error=str(err),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute experience recording."""
        return self.execute(input_data, context)


__all__ = [
    "ExperienceInput",
    "ExperienceOutput",
    "ExperiencePlugin",
]
