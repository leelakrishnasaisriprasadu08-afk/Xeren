"""Consistency and alignment verification tools."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from xeren.plugins.verification.schemas import CheckResult


class ConsistencyCheckerTool:
    """Audits candidate outputs for internal consistency, task alignment, and trajectory coherence."""

    CONTRADICTION_PAIRS = [
        (r"\b(always|must|definitely)\b", r"\b(never|cannot|impossible)\b"),
        (r"\b(increased|rose|grew)\b", r"\b(decreased|fell|dropped)\b"),
        (r"\b(success|succeeded|passed)\b", r"\b(failed|failure|error)\b"),
        (r"\b(supported|compatible)\b", r"\b(unsupported|incompatible)\b"),
        (r"\b(is true|was true)\b", r"\b(is false|was false)\b"),
    ]

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "with", "is", "was", "are", "were", "be", "been", "being", "have", "has",
        "had", "it", "its", "this", "that", "these", "those", "of", "as", "by",
        "how", "what", "which", "who", "when", "where", "why", "can", "could",
    }

    def check_consistency(
        self,
        candidate: Any,
        task: Optional[str] = None,
        context: Optional[str] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[CheckResult], float]:
        """
        Audit output consistency.

        Returns:
            (checks, consistency_score)
        """
        checks: List[CheckResult] = []
        candidate_text = candidate if isinstance(candidate, str) else str(candidate)

        # 1. Internal contradiction check
        contradiction_check = self._check_internal_contradiction(candidate_text)
        checks.append(contradiction_check)

        # 2. Task alignment check
        if task:
            alignment_check = self._check_task_alignment(candidate_text, task)
            checks.append(alignment_check)
        else:
            checks.append(
                CheckResult(
                    name="task_alignment_check",
                    passed=True,
                    score=1.0,
                    reason="No task specification provided; task alignment skipped.",
                )
            )

        # 3. Trajectory coherence check
        if trajectory:
            trajectory_check = self._check_trajectory_coherence(candidate_text, trajectory)
            checks.append(trajectory_check)
        else:
            checks.append(
                CheckResult(
                    name="trajectory_coherence_check",
                    passed=True,
                    score=1.0,
                    reason="No execution trajectory provided; trajectory coherence skipped.",
                )
            )

        scores = [c.score for c in checks]
        consistency_score = sum(scores) / len(scores) if scores else 1.0
        consistency_score = round(min(1.0, max(0.0, consistency_score)), 3)

        return checks, consistency_score

    def _check_internal_contradiction(self, text: str) -> CheckResult:
        # Check adjacent sentences or paragraph for direct contradictions on the same subject
        sentences = [s.strip().lower() for s in re.split(r"[.!?]\s+", text) if s.strip()]
        contradictions_found = []

        for i, s1 in enumerate(sentences):
            s1_clean = re.sub(r"\b(0|zero|no|without)\s+(errors?|failures?)\b", "", s1)
            for j, s2 in enumerate(sentences[i + 1 :], start=i + 1):
                s2_clean = re.sub(r"\b(0|zero|no|without)\s+(errors?|failures?)\b", "", s2)
                # Check for antonym pairs sharing significant noun/subject tokens
                s1_tokens = set(re.findall(r"\w+", s1_clean)) - self.STOPWORDS
                s2_tokens = set(re.findall(r"\w+", s2_clean)) - self.STOPWORDS
                common_entities = s1_tokens.intersection(s2_tokens)

                if common_entities:
                    for pattern_a, pattern_b in self.CONTRADICTION_PAIRS:
                        if (re.search(pattern_a, s1_clean) and re.search(pattern_b, s2_clean)) or (
                            re.search(pattern_b, s1_clean) and re.search(pattern_a, s2_clean)
                        ):
                            contradictions_found.append(
                                f"Contradiction regarding {common_entities}: '{s1[:50]}' vs '{s2[:50]}'"
                            )

        if contradictions_found:
            return CheckResult(
                name="internal_contradiction_check",
                passed=False,
                score=0.3,
                reason=f"Found {len(contradictions_found)} internal contradictions: {contradictions_found[0]}",
                actionable_correction="Resolve contradictory statements in the response to maintain a single coherent stance.",
                details={"contradictions": contradictions_found},
            )

        return CheckResult(
            name="internal_contradiction_check",
            passed=True,
            score=1.0,
            reason="No internal contradictions detected.",
        )

    META_INSTRUCTIONS: Set[str] = {
        "implement", "write", "create", "make", "generate", "build",
        "function", "code", "script", "program", "class", "method",
    }

    def _check_task_alignment(self, text: str, task: str) -> CheckResult:
        raw_tokens = [t for t in re.findall(r"\w+", task.lower()) if t not in self.STOPWORDS]
        if not raw_tokens:
            return CheckResult(
                name="task_alignment_check",
                passed=True,
                score=1.0,
                reason="Task contained no specific keywords to align against.",
            )

        # Filter out meta-instructions if domain keywords exist
        domain_tokens = [t for t in raw_tokens if t not in self.META_INSTRUCTIONS]
        task_tokens = domain_tokens if domain_tokens else raw_tokens

        text_tokens = set(re.findall(r"\w+", text.lower()))
        matched = []
        for t in task_tokens:
            if t in text_tokens:
                matched.append(t)
            elif len(t) >= 4:
                # Subword/prefix match (e.g. multiply <-> multiplication)
                prefix = t[:4]
                if any(w.startswith(prefix) or (len(w) >= 4 and t.startswith(w[:4])) for w in text_tokens):
                    matched.append(t)

        ratio = len(matched) / len(task_tokens)
        passed = (len(matched) >= 1 and len(task_tokens) <= 3) or ratio >= 0.25 or len(matched) >= 2
        score = round(min(1.0, max(0.0, max(ratio, 0.9 if passed else 0.2))), 3)

        return CheckResult(
            name="task_alignment_check",
            passed=passed,
            score=score,
            reason=f"Task keyword alignment ratio is {ratio:.2f} ({len(matched)}/{len(task_tokens)} keywords matched).",
            actionable_correction="Directly address the specific prompt/task requirements." if not passed else None,
            details={"matched_keywords": matched, "missing_keywords": list(set(task_tokens) - set(matched))},
        )

    def _check_trajectory_coherence(
        self, text: str, trajectory: List[Dict[str, Any]]
    ) -> CheckResult:
        # Detect if trajectory contained explicit tool errors that the candidate ignored
        has_tool_error = False
        error_details = []
        for step in trajectory:
            status = step.get("status", "").lower()
            error = step.get("error")
            output = str(step.get("output", ""))
            if status in ("failed", "error") or error or "traceback" in output.lower():
                has_tool_error = True
                error_details.append(str(error or output[:60]))

        text_lower = text.lower()
        if has_tool_error and ("succeeded" in text_lower or "successfully completed all" in text_lower):
            return CheckResult(
                name="trajectory_coherence_check",
                passed=False,
                score=0.4,
                reason="Candidate claims complete success despite execution errors recorded in trajectory.",
                actionable_correction="Acknowledge or address tool execution failures from trajectory in the final response.",
                details={"trajectory_errors": error_details[:3]},
            )

        return CheckResult(
            name="trajectory_coherence_check",
            passed=True,
            score=1.0,
            reason=f"Candidate is coherent with {len(trajectory)} trajectory steps.",
        )
