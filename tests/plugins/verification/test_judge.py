"""Tests for BaseJudge, MockJudge, and LLMJudge implementations."""

import json
import pytest

from xeren.models.providers.mock import MockLLM
from xeren.plugins.verification.schemas import EvidenceItem, JudgeVerdict
from xeren.plugins.verification.tools.judge import BaseJudge, LLMJudge, MockJudge


def test_mock_judge_default():
    """Verify MockJudge produces a valid verdict with default scores."""
    judge = MockJudge()
    verdict = judge.judge(
        task="Explain photosynthesis",
        candidate="Photosynthesis converts light into chemical energy.",
    )
    assert isinstance(verdict, JudgeVerdict)
    assert verdict.is_valid is True
    assert verdict.score == 1.0
    assert "Photosynthesis" not in verdict.rationale or verdict.rationale != ""
    assert "correctness" in verdict.criteria_scores


def test_mock_judge_empty_candidate():
    """Verify MockJudge rejects empty or whitespace candidate."""
    judge = MockJudge()
    verdict = judge.judge(task="Explain gravity", candidate="   ")
    assert verdict.is_valid is False
    assert verdict.score == 0.0
    assert len(verdict.suggested_improvements) >= 1


def test_mock_judge_preset_verdict():
    """Verify MockJudge respects preset verdict override."""
    preset = JudgeVerdict(
        is_valid=False,
        score=0.35,
        rationale="Insufficient depth for research level response.",
        criteria_scores={"depth": 0.35},
        suggested_improvements=["Provide citations to academic literature."],
    )
    judge = MockJudge(preset_verdict=preset)
    verdict = judge.judge(task="Review quantum computing", candidate="Quantum computers use qubits.")
    assert verdict is preset
    assert verdict.score == 0.35
    assert verdict.is_valid is False


def test_mock_judge_rubric_criteria():
    """Verify MockJudge populates criteria scores based on provided rubric."""
    judge = MockJudge(default_score=0.85)
    rubric = {"criteria": ["accuracy", "conciseness", "evidence_grounding"]}
    verdict = judge.judge(
        task="Summary",
        candidate="Here is the summary.",
        rubric=rubric,
    )
    assert verdict.criteria_scores["accuracy"] == 0.85
    assert verdict.criteria_scores["conciseness"] == 0.85
    assert verdict.criteria_scores["evidence_grounding"] == 0.85


@pytest.mark.asyncio
async def test_mock_judge_async():
    """Verify MockJudge ajudge operates asynchronously."""
    judge = MockJudge(default_valid=True, default_score=0.95)
    verdict = await judge.ajudge(task="Task", candidate="Answer")
    assert verdict.is_valid is True
    assert verdict.score == 0.95


def test_llm_judge_json_parsing():
    """Verify LLMJudge successfully parses JSON response from LLM."""
    canned_payload = json.dumps(
        {
            "is_valid": True,
            "score": 0.92,
            "rationale": "High quality answer accurately addressing user requirements.",
            "criteria_scores": {"accuracy": 0.95, "clarity": 0.90},
            "suggested_improvements": ["Add concrete usage example."],
        }
    )
    mock_llm = MockLLM(canned_response=f"```json\n{canned_payload}\n```")
    judge = LLMJudge(llm=mock_llm)

    verdict = judge.judge(
        task="How do I read a file in Python?",
        candidate="Use `with open('file.txt') as f: content = f.read()`",
    )
    assert verdict.is_valid is True
    assert verdict.score == 0.92
    assert "usage example" in verdict.suggested_improvements[0]
    assert len(mock_llm.call_history) == 1


@pytest.mark.asyncio
async def test_llm_judge_async():
    """Verify LLMJudge ajudge operates asynchronously."""
    canned_payload = json.dumps(
        {
            "is_valid": False,
            "score": 0.40,
            "rationale": "Candidate provides incorrect code syntax.",
            "criteria_scores": {"correctness": 0.30},
            "suggested_improvements": ["Fix syntax errors."],
        }
    )
    mock_llm = MockLLM(canned_response=canned_payload)
    judge = LLMJudge(llm=mock_llm)

    verdict = await judge.ajudge(
        task="Sort a list",
        candidate="broken python syntax",
    )
    assert verdict.is_valid is False
    assert verdict.score == 0.40


def test_llm_judge_fallback_parsing():
    """Verify LLMJudge falls back gracefully when output is non-JSON prose."""
    mock_llm = MockLLM(canned_response="This candidate response looks valid and well-reasoned overall.")
    judge = LLMJudge(llm=mock_llm)

    verdict = judge.judge(
        task="Define API",
        candidate="An Application Programming Interface defines interactions between software intermediaries.",
    )
    assert verdict.is_valid is True
    assert verdict.score >= 0.5
    assert len(verdict.rationale) > 0
