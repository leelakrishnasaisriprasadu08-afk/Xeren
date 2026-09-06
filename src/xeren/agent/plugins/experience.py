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
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)


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

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="experience",
            version="0.1.0",
            description="Transforms agent trajectory executions into verified ExperienceRecord datasets",
            capabilities=[PluginCapability.CUSTOM.value],
            input_schema_name="ExperienceInput",
            output_schema_name="ExperienceOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ExperienceInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ExperienceOutput

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
