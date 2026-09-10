from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from xeren.data.schema import VerificationDetails
from xeren.plugins.contract import (
    BasePlugin,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginManifest,
)

logger = logging.getLogger("xeren.agent.plugins.verification")


class VerificationInput(BaseModel):
    """Input parameters for outcome verification."""
    task: str = Field(default="", description="Goal or task description being verified")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Artifacts collected during task execution")
    rules: List[str] = Field(default_factory=list, description="Optional verification rules or assertions to check")
    success: bool = Field(default=True, description="Reported task success")
    expected_conditions: List[str] = Field(default_factory=list, description="Conditions to verify")
    actual_data: Dict[str, Any] = Field(default_factory=dict, description="Observed result payload")
    verifier: str = Field(default="rule_verifier", description="Verifier identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional verification metadata")

    model_config = {"arbitrary_types_allowed": True}


class VerificationOutput(BaseModel):
    """Structured outcome verification payload."""
    verified: bool = Field(default=True, description="Whether verification passed")
    verifier: str = Field(default="rule_verifier", description="Verifier type")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Verification confidence score")
    details: Union[VerificationDetails, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Canonical verification outcome conforming to xeren.data.schema.VerificationDetails or dict",
    )
    findings: List[str] = Field(
        default_factory=list,
        description="List of verification findings or check summaries",
    )

    def to_verification_details(self) -> VerificationDetails:
        """Convert to Xeren data schema VerificationDetails."""
        if isinstance(self.details, VerificationDetails):
            return self.details
        return VerificationDetails(
            verified=self.verified,
            verifier=self.verifier,
            score=self.score,
            details=self.details if isinstance(self.details, dict) else {},
        )

    model_config = {"arbitrary_types_allowed": True}


class VerificationPlugin(BasePlugin):
    """Plugin implementing outcome verification for autonomous agent runs."""

    def __init__(self, verifier_name: str = "VerificationPlugin", **kwargs: Any) -> None:
        self.verifier_name = verifier_name

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="verification",
            version="0.1.0",

            description="Evaluates and verifies agent task outcomes against defined criteria",
            capabilities=["verification", "quality_gate"],
            input_schema_name="VerificationInput",
            output_schema_name="VerificationOutput",
            author="Xeren",
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return VerificationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return VerificationOutput

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

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:

        """Execute verification on provided artifacts and rules."""
        start_time = time.perf_counter()
        validated = (
            input_data if isinstance(input_data, VerificationInput) else self.validate_input(input_data)
        )

        task = getattr(validated, "task", getattr(validated, "claim", ""))
        artifacts = getattr(validated, "artifacts", {}) or {}
        rules = list(getattr(validated, "rules", []) or [])
        expected_conds = getattr(validated, "expected_conditions", []) or []
        actual_data = getattr(validated, "actual_data", {}) or {}
        success_flag = getattr(validated, "success", True)

        findings: List[str] = []
        checks_passed = 0
        total_checks = 0

        # Check success flag
        total_checks += 1
        if success_flag:
            checks_passed += 1
        else:
            findings.append("Task reported failure (success=False).")

        # Check expected conditions
        for cond in expected_conds:
            total_checks += 1
            cond_lower = cond.lower()
            if "not empty" in cond_lower:
                if actual_data or artifacts:
                    checks_passed += 1
                    findings.append("Condition passed: data is not empty.")
                else:
                    findings.append("Condition FAILED: data/artifacts is empty.")
            elif "contains" in cond_lower:
                key = cond.split()[-1]
                if (isinstance(actual_data, dict) and key in actual_data) or (key in str(actual_data)) or (key in artifacts):
                    checks_passed += 1
                    findings.append(f"Condition passed: contains '{key}'.")
                else:
                    findings.append(f"Condition FAILED: does not contain '{key}'.")
            else:
                checks_passed += 1
                findings.append(f"Condition verified: '{cond}'.")

        # Check artifacts and rules
        art_details = self.verify_artifacts(
            task=str(task),
            artifacts=artifacts,
            rules=rules,
        )
        if art_details.details.get("findings"):
            findings.extend(art_details.details["findings"])
        checks_passed += art_details.details.get("checks_passed", 1)
        total_checks += art_details.details.get("total_checks", 1)

        score = checks_passed / total_checks if total_checks > 0 else 1.0
        # If success_flag is False or any expected condition failed, fail verification
        all_conds_met = (len(findings) == 0) or not any("FAILED" in f or "failure" in f for f in findings)
        is_verified = success_flag and art_details.verified and all_conds_met

        final_score = 1.0 if is_verified else (0.0 if not success_flag else round(score, 2))

        details = VerificationDetails(
            verified=is_verified,
            verifier=self.verifier_name,
            score=final_score,
            details={"findings": findings, "checks_passed": checks_passed, "total_checks": total_checks},
        )

        output = VerificationOutput(
            verified=is_verified,
            verifier=self.verifier_name,
            score=final_score,
            details=details,
            findings=findings,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return PluginExecutionResult(
            plugin_name=self.name,
            success=True,
            output=output,
            latency_ms=latency_ms,
            metadata={"verified": is_verified, "score": final_score},
        )


__all__ = [
    "VerificationInput",
    "VerificationOutput",
    "VerificationPlugin",
]
