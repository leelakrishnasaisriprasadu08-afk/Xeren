"""Unit tests for ExperienceRecord schema and type conversions."""

import pytest
from pydantic import ValidationError

from xeren.data.schema import (
    ActionStep,
    AlternativeCandidate,
    DatasetSplit,
    ExperienceRecord,
    RetrievalItem,
    VerificationDetails,
)


def test_experience_record_creation_and_serialization() -> None:
    rec = ExperienceRecord(
        sample_id="exp-001",
        task="Test task goal",
        plan=["Step 1", "Step 2"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Step 1",
                tool_name="calculator",
                tool_args={"expression": "10 * 5"},
                action_selection_rationale="Calculate product",
                result="50",
                success=True,
            )
        ],
        prediction_confidence=0.95,
        verification=VerificationDetails(
            verified=True,
            verifier="unit_test",
            score=0.99,
            details={"status": "ok"},
        ),
        alternatives=[
            AlternativeCandidate(
                candidate_action="python_eval",
                score=0.7,
                comparison_note="Calculator is more isolated",
                rejected_reason="Safety constraints",
            )
        ],
        retrieval_items=[
            RetrievalItem(
                source_id="doc1#c0",
                content="Doc content",
                is_useful=True,
                relevance_score=0.9,
            )
        ],
        success=True,
        failure_reason=None,
        recovery_strategy=None,
        final_quality_score=0.95,
        split=DatasetSplit.TRAIN,
        is_verified=True,
    )

    assert rec.sample_id == "exp-001"
    assert rec.prediction_confidence == 0.95
    assert rec.verification.verified is True
    assert rec.split == DatasetSplit.TRAIN
    assert rec.is_verified is True
    assert len(rec.actions) == 1
    assert rec.actions[0].tool_name == "calculator"

    # JSON round trip
    json_str = rec.model_dump_json()
    loaded = ExperienceRecord.model_validate_json(json_str)
    assert loaded.sample_id == rec.sample_id
    assert loaded.content_fingerprint() == rec.content_fingerprint()


def test_experience_record_validation_bounds() -> None:
    # Invalid confidence (< 0)
    with pytest.raises(ValidationError):
        ExperienceRecord(
            sample_id="err-1",
            task="Task",
            prediction_confidence=1.5,  # Out of bounds
            verification=VerificationDetails(verified=True, verifier="h", score=1.0),
            success=True,
            final_quality_score=0.8,
        )

    # Invalid quality score (< 0)
    with pytest.raises(ValidationError):
        ExperienceRecord(
            sample_id="err-2",
            task="Task",
            prediction_confidence=0.5,
            verification=VerificationDetails(verified=True, verifier="h", score=1.0),
            success=True,
            final_quality_score=-0.1,  # Out of bounds
        )


def test_to_eval_sample_integration() -> None:
    rec = ExperienceRecord(
        sample_id="exp-eval-01",
        task="What is Xeren?",
        plan=["Search docs"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Search docs",
                tool_name="rag_search",
                tool_args={"q": "Xeren"},
                result="Xeren is an AI framework.",
            )
        ],
        prediction_confidence=0.9,
        verification=VerificationDetails(verified=True, verifier="judge", score=0.9),
        retrieval_items=[
            RetrievalItem(source_id="intro#1", content="Xeren framework", is_useful=True, relevance_score=0.95),
            RetrievalItem(source_id="other#1", content="Unrelated notes", is_useful=False, relevance_score=0.1),
        ],
        success=True,
        final_quality_score=0.92,
        split=DatasetSplit.TEST,
        is_verified=True,
    )

    eval_sample = rec.to_eval_sample()
    assert eval_sample.sample_id == "exp-eval-01"
    assert eval_sample.query == "What is Xeren?"
    assert eval_sample.generated_answer == "Xeren is an AI framework."
    assert eval_sample.expected_source_ids == ["intro#1"]
    assert len(eval_sample.retrieved_chunks) == 2
    assert eval_sample.retrieved_chunks[0].chunk.chunk_id == "intro#1"
    assert eval_sample.metadata["split"] == "test"
