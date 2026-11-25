"""Tests for ResultRerankerTool (candidate scoring, sorting, task relevance, evidence grounding)."""

import pytest

from xeren.plugins.verification.schemas import CandidateItem, EvidenceItem
from xeren.plugins.verification.tools.reranker import ResultRerankerTool


@pytest.fixture
def reranker():
    return ResultRerankerTool()


def test_reranker_empty_list(reranker):
    """Verify empty candidate list returns empty list."""
    assert reranker.rerank([]) == []


def test_reranker_task_relevance(reranker):
    """Verify candidate with highest task overlap is ranked first."""
    task = "Find the latest population estimates for Tokyo Japan in 2025"
    candidates = [
        CandidateItem(id="cand_irrelevant", content="The weather in Madrid is sunny and warm today."),
        CandidateItem(
            id="cand_relevant",
            content="Tokyo Japan had an estimated metropolitan population of over 14 million residents in 2025.",
        ),
        CandidateItem(id="cand_partial", content="Japan has many beautiful cities to visit."),
    ]

    reranked = reranker.rerank(candidates=candidates, task=task)
    assert len(reranked) == 3
    assert reranked[0].id == "cand_relevant"
    assert reranked[0].score is not None
    assert reranked[0].score > (reranked[1].score or 0.0)
    assert reranked[0].score > (reranked[2].score or 0.0)


def test_reranker_evidence_grounding(reranker):
    """Verify candidate grounded in evidence is scored higher than ungrounded candidate."""
    evidence = [
        EvidenceItem(
            source_id="financial_report",
            content="Q3 net income reached 4.2 billion dollars, driven by cloud computing services growth.",
            confidence=1.0,
        )
    ]
    candidates = [
        CandidateItem(
            id="cand_grounded",
            content="Net income for Q3 reached 4.2 billion dollars due to cloud computing services expansion.",
        ),
        CandidateItem(
            id="cand_ungrounded",
            content="The company lost money and closed several retail department stores.",
        ),
    ]

    reranked = reranker.rerank(candidates=candidates, evidence=evidence)
    assert reranked[0].id == "cand_grounded"
    assert (reranked[0].score or 0.0) > (reranked[1].score or 0.0)
    assert "rerank_breakdown" in reranked[0].metadata


def test_reranker_preserves_candidate_metadata(reranker):
    """Verify candidate metadata is preserved and augmented with rerank breakdown."""
    candidates = [
        CandidateItem(id="c1", content="Alpha text sample", metadata={"custom_tag": "test_tag"}),
    ]
    reranked = reranker.rerank(candidates=candidates, task="Alpha test")
    assert reranked[0].metadata["custom_tag"] == "test_tag"
    assert "rerank_breakdown" in reranked[0].metadata
