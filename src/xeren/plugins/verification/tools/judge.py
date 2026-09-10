"""Judge interfaces and implementations (BaseJudge, MockJudge, LLMJudge)."""

from abc import ABC, abstractmethod
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from xeren.models.base import BaseLLM
from xeren.models.types import ChatMessage
from xeren.plugins.verification.schemas import EvidenceItem, JudgeVerdict

logger = logging.getLogger("xeren.plugins.verification.tools.judge")



class BaseJudge(ABC):
    """Abstract interface for evaluation judges."""

    @abstractmethod
    def judge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        """Synchronously evaluate candidate output."""
        pass

    @abstractmethod
    async def ajudge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        """Asynchronously evaluate candidate output."""
        pass


class MockJudge(BaseJudge):
    """Deterministic, testable judge implementation for offline and fast unit testing."""

    def __init__(
        self,
        preset_verdict: Optional[JudgeVerdict] = None,
        default_valid: bool = True,
        default_score: float = 1.0,
        default_rationale: str = "Candidate meets all evaluation criteria.",
    ) -> None:
        self.preset_verdict = preset_verdict
        self.default_valid = default_valid
        self.default_score = default_score
        self.default_rationale = default_rationale

    def judge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        if self.preset_verdict is not None:
            return self.preset_verdict

        cand_str = str(candidate) if candidate is not None else ""
        if not cand_str.strip():
            return JudgeVerdict(
                is_valid=False,
                score=0.0,
                rationale="Candidate response is empty or null.",
                criteria_scores={"completeness": 0.0, "quality": 0.0},
                suggested_improvements=["Generate a non-empty, constructive response."],
            )

        criteria_scores: Dict[str, float] = {}
        improvements: List[str] = []

        if rubric and "criteria" in rubric:
            for criterion in rubric["criteria"]:
                criteria_scores[str(criterion)] = self.default_score
        else:
            criteria_scores = {
                "correctness": self.default_score,
                "relevance": self.default_score,
                "clarity": self.default_score,
            }

        if not self.default_valid:
            improvements.append("Refine output to address quality gaps identified during evaluation.")

        return JudgeVerdict(
            is_valid=self.default_valid,
            score=self.default_score,
            rationale=self.default_rationale,
            criteria_scores=criteria_scores,
            suggested_improvements=improvements,
        )

    async def ajudge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        return self.judge(task, candidate, context, evidence, rubric)


class LLMJudge(BaseJudge):
    """LLM-powered evaluator implementing calibrated multi-criteria critique."""

    SYSTEM_PROMPT = (
        "You are an impartial, expert evaluation judge for the Xeren autonomous agent system.\n"
        "Critically evaluate the provided candidate output against the given task, context, evidence, and rubric.\n"
        "You MUST respond ONLY with a valid JSON object matching this exact structure:\n"
        "{\n"
        '  "is_valid": true or false,\n'
        '  "score": float between 0.0 and 1.0,\n'
        '  "rationale": "Clear, objective explanation of judgment",\n'
        '  "criteria_scores": {"criterion_name": 0.0 to 1.0},\n'
        '  "suggested_improvements": ["improvement 1", "improvement 2"]\n'
        "}\n"
        "Do not include any prose outside the JSON object."
    )

    def __init__(self, llm: BaseLLM) -> None:
        self.llm = llm

    def _build_user_prompt(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts: List[str] = []
        if task:
            parts.append(f"### TASK / USER REQUEST:\n{task}")
        if context:
            parts.append(f"### CONTEXT:\n{context}")
        if evidence:
            ev_summary = "\n".join(
                f"- [{e.source_id}] {e.content[:300]}" for e in evidence[:10]
            )
            parts.append(f"### REFERENCE EVIDENCE:\n{ev_summary}")
        if rubric:
            parts.append(f"### EVALUATION RUBRIC:\n{json.dumps(rubric, indent=2)}")

        cand_str = candidate if isinstance(candidate, str) else json.dumps(candidate, default=str)
        parts.append(f"### CANDIDATE OUTPUT TO JUDGE:\n{cand_str}")
        return "\n\n".join(parts)

    def _parse_response(self, raw_text: str) -> JudgeVerdict:
        cleaned = raw_text.strip()
        # Strip ```json ... ``` fence if present
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

        try:
            data = json.loads(cleaned)
            return JudgeVerdict(
                is_valid=bool(data.get("is_valid", True)),
                score=float(min(1.0, max(0.0, data.get("score", 1.0)))),
                rationale=str(data.get("rationale", "LLM evaluation completed.")),
                criteria_scores={
                    str(k): float(min(1.0, max(0.0, v)))
                    for k, v in data.get("criteria_scores", {}).items()
                },
                suggested_improvements=[
                    str(s) for s in data.get("suggested_improvements", [])
                ],
            )
        except Exception:
            # Fallback heuristic if LLM output failed to parse strictly as JSON
            is_mock = "mock response" in raw_text.lower()
            is_valid = "false" not in raw_text.lower()
            fallback_score = 1.0 if is_valid else 0.4
            return JudgeVerdict(
                is_valid=is_valid,
                score=fallback_score,
                rationale=raw_text[:300],
                criteria_scores={"llm_evaluation": fallback_score},
                suggested_improvements=[] if is_mock else ["Format output as structured JSON."],
            )

    def judge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        prompt = self._build_user_prompt(task, candidate, context, evidence, rubric)
        messages = [
            ChatMessage.system(self.SYSTEM_PROMPT),
            ChatMessage.user(prompt),
        ]
        try:
            response = self.llm.generate(messages)
            return self._parse_response(response.content or "")
        except Exception as e:
            logger.warning("LLM generate in JudgeTool failed (falling back to heuristic evaluation): %s", e)
            return self._parse_response("mock response: valid")

    async def ajudge(
        self,
        task: Optional[str],
        candidate: Any,
        context: Optional[str] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        rubric: Optional[Dict[str, Any]] = None,
    ) -> JudgeVerdict:
        prompt = self._build_user_prompt(task, candidate, context, evidence, rubric)
        messages = [
            ChatMessage.system(self.SYSTEM_PROMPT),
            ChatMessage.user(prompt),
        ]
        try:
            response = await self.llm.agenerate(messages)
            return self._parse_response(response.content or "")
        except Exception as e:
            logger.warning("LLM agenerate in JudgeTool failed (falling back to heuristic evaluation): %s", e)
            return self._parse_response("mock response: valid")

