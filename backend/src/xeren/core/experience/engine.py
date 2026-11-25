"""
Xeren ExperienceStore Causal Engine — Central Orchestrator
==========================================================
Coordinates the complete causal learning lifecycle:
1. Trace Ingestion & Causal Lesson Distillation (Action, Result, RootCause, NewStrategy)
2. Anti-Poison Quarantine Staging & Credential Sanitization
3. Verification-Gated Promotion into Authoritative SQLite Storage
4. Pre-Execution Causal Advisory for Agents & Specialist M12
5. Continual Learning Training Dataset Pipeline for M12 Fine-Tuning
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .distiller import CausalDistiller
from .models import (
    CausalAdvisory,
    CausalRecommendation,
    CausalTuple,
    CausalWarning,
    ReviewStatus,
)
from .quarantine_gate import AntiPoisonQuarantineGate
from .store import CausalExperienceStore

logger = logging.getLogger("xeren.core.experience.engine")

M12_SYSTEM_PROMPT = (
    "You are Xeren M12 Experience, the sovereign Experience & Learning Specialist within the Xeren MoS architecture.\n"
    "Your role is to recall past causal outcomes, diagnose root causes of failures, and prescribe proven operational strategies."
)


class ExperienceStoreCausalEngine:
    """Sovereign Causal Engine managing distillation, anti-poison quarantine, and pre-execution advisory."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        quarantine_path: Optional[Path] = None,
        distiller: Optional[CausalDistiller] = None,
    ) -> None:
        self.store = CausalExperienceStore(db_path=db_path)
        self.quarantine = AntiPoisonQuarantineGate(staging_path=quarantine_path)
        self.distiller = distiller or CausalDistiller()

    def record_trace(
        self,
        task_id: str,
        objective: str,
        action: str,
        result: str,
        success: bool,
        error: Optional[str] = None,
        verification_score: float = 1.0,
        auto_approve_threshold: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CausalTuple:
        """
        Record and distill an execution trace into a causal tuple.
        Passes through the Anti-Poison Quarantine Gate.
        Automatically promotes verified successful traces if score >= auto_approve_threshold.
        """
        # 1. Distill causal lesson
        raw_tuple = self.distiller.distill(
            task_id=task_id,
            objective=objective,
            action=action,
            result=result,
            success=success,
            error=error,
            verification_score=verification_score,
            metadata=metadata,
        )

        # 2. Stage through Anti-Poison Quarantine (PII sanitized)
        staged_tuple = self.quarantine.stage(raw_tuple)

        # 3. Defensive Gate: auto-promote only if verified success with high score
        if success and verification_score >= auto_approve_threshold:
            staged_tuple.status = ReviewStatus.APPROVED
            self.store.save(staged_tuple)
            self.quarantine.update_status(staged_tuple.fingerprint, ReviewStatus.APPROVED)
            logger.info(
                "[CausalEngine] Auto-promoted verified success into store (fingerprint: %s)",
                staged_tuple.fingerprint[:8],
            )

        return staged_tuple

    def review_experience(
        self,
        fingerprint: str,
        approve: bool,
    ) -> Optional[CausalTuple]:
        """Human-in-the-loop or automated supervisor review of quarantined experiences."""
        new_status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
        updated = self.quarantine.update_status(fingerprint, new_status)
        if not updated:
            return None

        if approve:
            self.store.save(updated)
            logger.info("[CausalEngine] Promoted experience to store (fingerprint: %s)", fingerprint[:8])
        return updated

    def advise(
        self,
        objective: str,
        proposed_action: str,
        top_k: int = 5,
    ) -> CausalAdvisory:
        """
        Pre-execution advisory for agents before running an action.
        Searches past failures and successes to issue warnings and recommendations.
        """
        query = f"{objective} {proposed_action}"

        # 1. Look for relevant past failures
        past_failures = self.store.search(
            query=query,
            success_only=False,
            approved_only=True,
            limit=top_k,
        )

        warnings: List[CausalWarning] = []
        for fail in past_failures:
            severity = "high" if "permission" in (fail.root_cause or "").lower() else "medium"
            warnings.append(
                CausalWarning(
                    past_action=fail.action,
                    failure_reason=fail.result[:180],
                    root_cause=fail.root_cause or "Unknown cause",
                    avoidance_advice=fail.new_strategy or "Proceed with caution",
                    severity=severity,
                    fingerprint=fail.fingerprint,
                )
            )

        # 2. Look for relevant past successes
        past_successes = self.store.search(
            query=query,
            success_only=True,
            approved_only=True,
            limit=top_k,
        )

        recommendations: List[CausalRecommendation] = []
        for succ in past_successes:
            recommendations.append(
                CausalRecommendation(
                    past_action=succ.action,
                    proven_strategy=succ.new_strategy or f"Use {succ.action}",
                    confidence=succ.verification_score,
                    fingerprint=succ.fingerprint,
                )
            )

        # Determine advisory verdict
        should_proceed = True
        suggested_strategy = None

        if warnings:
            # If critical warning exists matching action directly
            direct_matches = [w for w in warnings if proposed_action.lower() in w.past_action.lower()]
            if direct_matches:
                should_proceed = False
                suggested_strategy = direct_matches[0].avoidance_advice
        elif recommendations:
            suggested_strategy = recommendations[0].proven_strategy

        confidence = 0.95 if (warnings or recommendations) else 0.50

        return CausalAdvisory(
            objective=objective,
            proposed_action=proposed_action,
            should_proceed=should_proceed,
            confidence=confidence,
            warnings=warnings,
            recommendations=recommendations,
            suggested_strategy=suggested_strategy,
        )

    def export_m12_dataset(
        self,
        output_path: Path,
        min_verification_score: float = 0.8,
    ) -> int:
        """
        Export approved causal tuples into clean JSONL training data for Specialist M12 (Experience).
        """
        records = self.store.list_all(status=ReviewStatus.APPROVED, limit=5000)
        eligible = [r for r in records if r.verification_score >= min_verification_score]

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for item in eligible:
                user_content = (
                    f"[OBJECTIVE: {item.objective}]\n"
                    f"Action Attempted: {item.action}\n"
                    f"Observed Result: {item.result}"
                )
                assistant_payload = {
                    "task_id": item.task_id,
                    "success": item.success,
                    "root_cause": item.root_cause,
                    "recommended_strategy": item.new_strategy,
                    "confidence": item.verification_score,
                }

                sample = {
                    "messages": [
                        {"role": "system", "content": M12_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": json.dumps(assistant_payload, indent=2)},
                    ]
                }
                f.write(json.dumps(sample) + "\n")
                count += 1

        logger.info("[CausalEngine] Exported %d samples to %s", count, output_path)
        return count
