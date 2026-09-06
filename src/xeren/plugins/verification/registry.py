"""Tool registry coordinating validation, evidence, consistency, reranking, judge, and scoring tools."""

from typing import Optional

from xeren.models.base import BaseLLM
from xeren.plugins.verification.tools.confidence import ConfidenceScorerTool
from xeren.plugins.verification.tools.consistency import ConsistencyCheckerTool
from xeren.plugins.verification.tools.evidence import SourceEvidenceTool
from xeren.plugins.verification.tools.judge import BaseJudge, LLMJudge, MockJudge
from xeren.plugins.verification.tools.reranker import ResultRerankerTool
from xeren.plugins.verification.tools.validator import StructuralValidatorTool


class VerificationToolRegistry:
    """Aggregates and configures all modular verification tools and judge evaluators."""

    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        judge: Optional[BaseJudge] = None,
        validator_tool: Optional[StructuralValidatorTool] = None,
        evidence_tool: Optional[SourceEvidenceTool] = None,
        consistency_tool: Optional[ConsistencyCheckerTool] = None,
        reranker_tool: Optional[ResultRerankerTool] = None,
        confidence_tool: Optional[ConfidenceScorerTool] = None,
    ) -> None:
        self.validator_tool = validator_tool or StructuralValidatorTool()
        self.evidence_tool = evidence_tool or SourceEvidenceTool()
        self.consistency_tool = consistency_tool or ConsistencyCheckerTool()
        self.reranker_tool = reranker_tool or ResultRerankerTool()
        self.confidence_tool = confidence_tool or ConfidenceScorerTool()

        if judge is not None:
            self.judge = judge
        elif llm is not None:
            self.judge = LLMJudge(llm=llm)
        else:
            self.judge = MockJudge()

    def set_llm(self, llm: Optional[BaseLLM]) -> None:
        """Update or inject LLM provider for judge critiques."""
        if llm is not None:
            self.judge = LLMJudge(llm=llm)
        else:
            self.judge = MockJudge()

    def set_judge(self, judge: BaseJudge) -> None:
        """Explicitly set a custom or test judge."""
        self.judge = judge


__all__ = ["VerificationToolRegistry"]
