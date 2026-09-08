 feature/core-architecture
"""ExperiencePlugin converting TaskState to canonical ExperienceRecord and persisting to ExperienceDataset."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from xeren.agent.state import TaskState, TaskStatus
from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    VerificationDetails,
)
from xeren.plugins.contract import (
    BasePlugin,

"""Experience Plugin capturing agent trajectories and generating ExperienceRecords."""

import json
from typing import Any, Dict, List, Optional, Type, Union
import uuid
from pydantic import BaseModel, Field

from xeren.agent.types import AgentState
from xeren.data.schema import ActionStep, DatasetSplit, ExperienceRecord, VerificationDetails
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
 main
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)

 feature/core-architecture
logger = logging.getLogger("xeren.agent.plugins.experience")


class ExperienceInput(BaseModel):
    """Input payload for recording task outcomes."""

    record: Optional[ExperienceRecord] = Field(
        default=None,
        description="Explicit ExperienceRecord to store",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata tags",
    )

    model_config = {"arbitrary_types_allowed": True}


class ExperienceOutput(BaseModel):
    """Output summary of experience recording."""

    success: bool = Field(
        ...,
        description="Whether the experience record was successfully added",
    )
    sample_id: str = Field(
        ...,
        description="Identifier of the recorded experience sample",
    )
    total_records: int = Field(
        default=0,
        description="Total count of experience records stored in dataset",
    )

    model_config = {"arbitrary_types_allowed": True}


class ExperiencePlugin(BasePlugin):
    """Modular plugin that captures agent trajectories into canonical ExperienceRecord and ExperienceDataset.

    Records both successful and failed task executions.
    """

    def __init__(self, dataset: Optional[ExperienceDataset] = None) -> None:
        self.dataset = dataset if dataset is not None else ExperienceDataset()


class ExperienceInput(BaseModel):
    """Input payload for experience recording."""

    state: Dict[str, Any] = Field(..., description="AgentState dictionary or serialized data")
    prediction_confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    final_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    split: str = Field(default="train", description="Target dataset split")
    verification_passed: bool = Field(default=True)
    verifier: str = Field(default="system")


class ExperienceOutput(BaseModel):
    """Generated experience record payload."""

    record: ExperienceRecord = Field(..., description="Constructed ExperienceRecord")
    fingerprint: str = Field(..., description="Content hash fingerprint")


class ExperiencePlugin(BasePlugin):
    """Plugin transforming agent trajectory executions into verified training experience data."""
 main

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="experience",
            version="0.1.0",
 feature/core-architecture
            description="Trajectory experience recording plugin for Xeren Autonomous Agent",
            capabilities=["experience_recording", "trajectory_logging"],
            input_schema_name="ExperienceInput",
            output_schema_name="ExperienceOutput",
            author="Xeren",

            description="Transforms agent trajectory executions into verified ExperienceRecord datasets",
            capabilities=[PluginCapability.CUSTOM.value],
            input_schema_name="ExperienceInput",
            output_schema_name="ExperienceOutput",
 main
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ExperienceInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ExperienceOutput

 feature/core-architecture
    def record_task_state(
        self,
        state: TaskState,
        verification: Optional[VerificationDetails] = None,
        prediction_confidence: float = 1.0,
    ) -> ExperienceRecord:
        """Convert a TaskState trajectory into an ExperienceRecord and store in dataset."""
        logger.info("Recording experience trajectory for task '%s' (status: %s)", state.task_id, state.status.value)

        # 1. Convert execution history into ActionSteps
        action_steps: List[ActionStep] = []
        step_idx = 0

        # Include completed steps
        for res in state.completed_steps:
            target_name = res.metadata.get("target", res.metadata.get("plugin_name", "unknown"))
            action_steps.append(
                ActionStep(
                    step_index=step_idx,
                    plan_step=f"Step {step_idx}: Execute {target_name}",
                    tool_name=target_name,
                    tool_args=res.metadata,
                    result=str(res.output) if res.output is not None else "success",
                    success=res.success,
                    error_message=res.error,
                )
            )
            step_idx += 1

        # Include failed steps
        for res in state.failed_steps:
            target_name = res.metadata.get("target", res.metadata.get("plugin_name", "unknown"))
            action_steps.append(
                ActionStep(
                    step_index=step_idx,
                    plan_step=f"Step {step_idx}: Execute {target_name} (failed)",
                    tool_name=target_name,
                    tool_args=res.metadata,
                    result="failed",
                    success=False,
                    error_message=res.error,
                    correction=state.metadata.get("recovery_strategy"),
                )
            )
            step_idx += 1

        # 2. Extract or formulate plan string list
        plan_list = [f"{a.action_type}:{a.target}" for a in state.remaining_steps]
        if not plan_list and action_steps:
            plan_list = [s.plan_step for s in action_steps]

        # 3. Formulate verification details if not supplied
        verif = verification or VerificationDetails(
            verified=state.status == TaskStatus.COMPLETED,
            verifier="task_completion_evaluator",
            score=1.0 if state.status == TaskStatus.COMPLETED else 0.0,
            details={"status": state.status.value, "completed_steps": len(state.completed_steps)},
        )

        # 4. Overall outcome evaluation
        is_success = (state.status == TaskStatus.COMPLETED)
        failure_reason = None
        if not is_success:
            if state.failed_steps and state.failed_steps[-1].error:
                failure_reason = state.failed_steps[-1].error
            else:
                failure_reason = f"Task terminated with status: {state.status.value}"

        quality_score = 1.0 if is_success else 0.0
        if is_success and verif.score:
            quality_score = verif.score

        # 5. Construct canonical ExperienceRecord
        record = ExperienceRecord(
            sample_id=state.task_id,
            task=state.goal,
            plan=plan_list,
            actions=action_steps,
            prediction_confidence=prediction_confidence,
            verification=verif,
            success=is_success,
            failure_reason=failure_reason,
            recovery_strategy=state.metadata.get("recovery_strategy"),
            final_quality_score=quality_score,
            split=DatasetSplit.TRAIN,
            is_verified=verif.verified,
            metadata={
                "task_id": state.task_id,
                "status": state.status.value,
                "attempt_count": state.attempt_count,
                "artifacts_count": len(state.artifacts),
                **state.metadata,
            },
        )

        # 6. Add to dataset
        self.dataset.add(record, enforce_verified=False)
        return record

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Execute experience plugin operation."""
        start_time = time.perf_counter()
        validated: ExperienceInput = (
            input_data if isinstance(input_data, ExperienceInput) else self.validate_input(input_data)  # type: ignore
        )

        if validated.record is not None:
            self.dataset.add(validated.record, enforce_verified=False)
            output = ExperienceOutput(
                success=True,
                sample_id=validated.record.sample_id,
                total_records=len(self.dataset),
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=output,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        return PluginExecutionResult(
            plugin_name=self.name,
            success=False,
            error="No ExperienceRecord provided in input.",
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )


__all__ = [
    "ExperienceInput",
    "ExperienceOutput",
    "ExperiencePlugin",
]

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        validated = self.validate_input(input_data)
        assert isinstance(validated, ExperienceInput)

        state_dict = validated.state
        task = state_dict.get("task", "Agent Execution Task")
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

        record = ExperienceRecord(
            sample_id=str(uuid.uuid4()),
            task=task,
            plan=plan,
            actions=action_steps,
            prediction_confidence=validated.prediction_confidence,
            verification=verification,
            success=validated.verification_passed,
            final_quality_score=validated.final_quality_score,
            split=DatasetSplit(validated.split) if validated.split in DatasetSplit._value2member_map_ else DatasetSplit.TRAIN,
            is_verified=validated.verification_passed,
            metadata={"source": "autonomous_work_agent"},
        )

        output = ExperienceOutput(
            record=record,
            fingerprint=record.content_fingerprint(),
        )

        return PluginExecutionResult(
            plugin_name=self.name,
            success=True,
            output=output,
            latency_ms=1.0,
        )


__all__ = ["ExperienceInput", "ExperienceOutput", "ExperiencePlugin"]
 main
