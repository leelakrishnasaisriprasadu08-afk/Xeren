"""Xeren Plugin #7: Verification Plugin.

Independent quality-control and outcome evaluation layer across modalities (text, code, data,
facts, and structure) providing deterministic validation, evidence grounding, consistency auditing,
candidate reranking, LLM judge evaluation, and calibrated confidence scoring.
"""

from xeren.plugins.verification.manifest import VERIFICATION_PLUGIN_MANIFEST
from xeren.plugins.verification.plugin import VerificationPlugin
from xeren.plugins.verification.registry import VerificationToolRegistry
from xeren.plugins.verification.schemas import (
    CandidateItem,
    CheckResult,
    EvidenceItem,
    JudgeVerdict,
    VerificationInput,
    VerificationOperation,
    VerificationResult,
    VerificationStatus,
)
from xeren.plugins.verification.tools.confidence import ConfidenceScorerTool
from xeren.plugins.verification.tools.consistency import ConsistencyCheckerTool
from xeren.plugins.verification.tools.evidence import SourceEvidenceTool
from xeren.plugins.verification.tools.judge import BaseJudge, LLMJudge, MockJudge
from xeren.plugins.verification.tools.reranker import ResultRerankerTool
from xeren.plugins.verification.tools.validator import StructuralValidatorTool
from xeren.plugins.verification.workflow import VerificationWorkflow

__all__ = [
    "VerificationPlugin",
    "VERIFICATION_PLUGIN_MANIFEST",
    "VerificationToolRegistry",
    "VerificationWorkflow",
    "VerificationInput",
    "VerificationResult",
    "VerificationOperation",
    "VerificationStatus",
    "EvidenceItem",
    "CandidateItem",
    "CheckResult",
    "JudgeVerdict",
    "StructuralValidatorTool",
    "SourceEvidenceTool",
    "ConsistencyCheckerTool",
    "ResultRerankerTool",
    "ConfidenceScorerTool",
    "BaseJudge",
    "MockJudge",
    "LLMJudge",
]
