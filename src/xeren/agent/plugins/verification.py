"""Verification Plugin validating agent execution outcomes and criteria."""

from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field

from xeren.data.schema import VerificationDetails
from xeren.plugins.contract import (
    BasePlugin,
    PluginCapability,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)


class VerificationInput(BaseModel):
    """Input parameters for outcome verification."""

    task: str = Field(..., description="Task or goal description")
    success: bool = Field(default=True, description="Reported task success")
    expected_conditions: List[str] = Field(default_factory=list, description="Conditions to verify")
    actual_data: Dict[str, Any] = Field(default_factory=dict, description="Observed result payload")
    verifier: str = Field(default="rule_verifier", description="Verifier identifier")


class VerificationOutput(BaseModel):
    """Structured outcome verification payload."""

    verified: bool = Field(..., description="Whether verification passed")
    verifier: str = Field(..., description="Verifier type")
    score: float = Field(..., ge=0.0, le=1.0, description="Verification confidence score")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic notes")

    def to_verification_details(self) -> VerificationDetails:
        """Convert to Xeren data schema VerificationDetails."""
        return VerificationDetails(
            verified=self.verified,
            verifier=self.verifier,
            score=self.score,
            details=self.details,
        )


class VerificationPlugin(BasePlugin):
    """Plugin implementing outcome verification for autonomous agent runs."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="verification",
            version="0.1.0",
            description="Evaluates and verifies agent task outcomes against defined criteria",
            capabilities=[PluginCapability.CUSTOM.value, PluginCapability.CODE_VERIFICATION.value],
            input_schema_name="VerificationInput",
            output_schema_name="VerificationOutput",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return VerificationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return VerificationOutput

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        validated = self.validate_input(input_data)
        assert isinstance(validated, VerificationInput)

        checks_passed = validated.success
        details: Dict[str, Any] = {"checks": len(validated.expected_conditions)}

        for cond in validated.expected_conditions:
            cond_lower = cond.lower()
            if "not empty" in cond_lower:
                passed = bool(validated.actual_data)
                checks_passed = checks_passed and passed
                details[cond] = passed
            elif "contains" in cond_lower:
                key = cond.split("contains", 1)[-1].strip()
                passed = key in validated.actual_data
                checks_passed = checks_passed and passed
                details[cond] = passed

        score = 1.0 if checks_passed else 0.0
        output = VerificationOutput(
            verified=checks_passed,
            verifier=validated.verifier,
            score=score,
            details=details,
        )

        return PluginExecutionResult(
            plugin_name=self.name,
            success=True,
            output=output,
            latency_ms=1.0,
        )


__all__ = ["VerificationInput", "VerificationOutput", "VerificationPlugin"]
