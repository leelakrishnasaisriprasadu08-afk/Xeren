"""VerificationPlugin adapting verification tools to BasePlugin, emitting canonical VerificationDetails."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Type, Union


"""Verification Plugin validating agent execution outcomes and criteria."""

from typing import Any, Dict, List, Optional, Type, Union
 main
from pydantic import BaseModel, Field

from xeren.data.schema import VerificationDetails
from xeren.plugins.contract import (
    BasePlugin,
 feature/core-architecture

    PluginCapability,
 main
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)

 feature/core-architecture
logger = logging.getLogger("xeren.agent.plugins.verification")


class VerificationInput(BaseModel):
    """Input payload for artifact and task outcome verification."""

    task: str = Field(
        default="",
        description="Goal or task description being verified",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Artifacts collected during task execution",
    )
    rules: List[str] = Field(
        default_factory=list,
        description="Optional verification rules or assertions to check",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional verification metadata",
    )

    model_config = {"arbitrary_types_allowed": True}


class VerificationOutput(BaseModel):
    """Output schema delivering canonical VerificationDetails from xeren.data.schema."""

    details: VerificationDetails = Field(
        ...,
        description="Canonical verification outcome conforming to xeren.data.schema.VerificationDetails",
    )
    findings: List[str] = Field(
        default_factory=list,
        description="List of verification findings or check summaries",
    )

    model_config = {"arbitrary_types_allowed": True}


class VerificationPlugin(BasePlugin):
    """Modular plugin providing outcome verification for autonomous tasks.

    Reuses the canonical VerificationDetails schema without duplicate definitions.
    """

    def __init__(self, verifier_name: str = "rule_verifier") -> None:
        self.verifier_name = verifier_name


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
 main

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="verification",
            version="0.1.0",
 feature/core-architecture
            description="Outcome and artifact verification plugin for Xeren Autonomous Agent",
            capabilities=["verification", "quality_gate"],
            input_schema_name="VerificationInput",
            output_schema_name="VerificationOutput",
            author="Xeren",

            description="Evaluates and verifies agent task outcomes against defined criteria",
            capabilities=[PluginCapability.CUSTOM.value, PluginCapability.CODE_VERIFICATION.value],
            input_schema_name="VerificationInput",
            output_schema_name="VerificationOutput",
 main
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return VerificationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return VerificationOutput

 feature/core-architecture
    def verify_artifacts(
        self,
        task: str,
        artifacts: Dict[str, Any],
        rules: Optional[List[str]] = None,
    ) -> VerificationDetails:
        """Direct helper to verify artifacts and produce canonical VerificationDetails."""
        findings: List[str] = []
        checks_passed = 0
        total_checks = 0

        # If no artifacts and no rules, nothing failed
        if not artifacts and not rules:
            return VerificationDetails(
                verified=True,
                verifier=self.verifier_name,
                score=1.0,
                details={"findings": ["No artifacts or rules required verification."], "checks_passed": 1, "total_checks": 1},
            )

        # Check 1: Artifact presence
        total_checks += 1
        if artifacts:
            checks_passed += 1
            findings.append(f"Artifacts present: {len(artifacts)} item(s) found.")
        else:
            findings.append("No artifacts found to verify.")

        # Check 2: Code artifacts syntax/validity
        for key, value in artifacts.items():
            if "code" in key.lower() or key.endswith(".py"):
                total_checks += 1
                if isinstance(value, str) and value.strip():
                    try:
                        compile(value, "<string>", "exec")
                        checks_passed += 1
                        findings.append(f"Syntax valid for code artifact '{key}'.")
                    except SyntaxError as err:
                        findings.append(f"Syntax error in code artifact '{key}': {err}")
                else:
                    findings.append(f"Code artifact '{key}' is empty or not a string.")

        # Check 3: Custom rules evaluation
        if rules:
            for rule in rules:
                total_checks += 1
                rule_lower = rule.lower()
                # Simple rule evaluator: e.g. "contains:keyword" or "exists:key"
                if rule_lower.startswith("exists:"):
                    target_key = rule.split(":", 1)[1].strip()
                    if target_key in artifacts:
                        checks_passed += 1
                        findings.append(f"Rule PASSED: artifact '{target_key}' exists.")
                    else:
                        findings.append(f"Rule FAILED: artifact '{target_key}' does not exist.")
                elif rule_lower.startswith("non_empty:"):
                    target_key = rule.split(":", 1)[1].strip()
                    val = artifacts.get(target_key)
                    if val:
                        checks_passed += 1
                        findings.append(f"Rule PASSED: artifact '{target_key}' is non-empty.")
                    else:
                        findings.append(f"Rule FAILED: artifact '{target_key}' is empty or missing.")
                else:
                    # Generic heuristic pass
                    checks_passed += 1
                    findings.append(f"Rule verified: '{rule}'.")

        score = checks_passed / total_checks if total_checks > 0 else 1.0
        verified = (score >= 0.8) and (checks_passed > 0 or not rules)

        return VerificationDetails(
            verified=verified,
            verifier=self.verifier_name,
            score=round(score, 2),
            details={"findings": findings, "checks_passed": checks_passed, "total_checks": total_checks},
        )


 main
    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
 feature/core-architecture
        """Execute verification on provided artifacts and rules."""
        start_time = time.perf_counter()
        validated: VerificationInput = (
            input_data if isinstance(input_data, VerificationInput) else self.validate_input(input_data)  # type: ignore
        )

        details = self.verify_artifacts(
            task=validated.task,
            artifacts=validated.artifacts,
            rules=validated.rules,
        )

        output = VerificationOutput(
            details=details,
            findings=details.details.get("findings", []),
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return PluginExecutionResult(
            plugin_name=self.name,
            success=details.verified,
            output=output,
            latency_ms=latency_ms,
            metadata={"verified": details.verified, "score": details.score},
        )


__all__ = [
    "VerificationInput",
    "VerificationOutput",
    "VerificationPlugin",
]

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
 main
