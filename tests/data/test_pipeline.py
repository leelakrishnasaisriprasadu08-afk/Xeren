"""Unit and integration tests for TrainingDataPipeline."""

from pathlib import Path
import json
import pytest

from xeren.data.dataset import ExperienceDataset
from xeren.data.pipeline import PipelineManifest, TrainingDataPipeline
from xeren.data.schema import (
    ActionStep,
    AlternativeCandidate,
    DatasetSplit,
    ExperienceRecord,
    RetrievalItem,
    ReviewStatus,
    VerificationDetails,
)


def _sample_experience(sample_id: str, split: DatasetSplit = DatasetSplit.TRAIN, success: bool = True) -> ExperienceRecord:
    failure_reason = None if success else "External failure"
    return ExperienceRecord(
        sample_id=sample_id,
        task=f"Task for {sample_id}",
        plan=["Execute action step"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Execute action step",
                tool_name="test_tool",
                tool_args={"arg": sample_id},
                result="Result output",
                success=success,
            )
        ],
        prediction_confidence=0.92,
        verification=VerificationDetails(
            verified=True,
            verifier="test_verifier",
            score=0.95,
            details={},
        ),
        alternatives=[
            AlternativeCandidate(
                candidate_action="alt_action",
                score=0.5,
                comparison_note="Worse option",
                rejected_reason="Suboptimal performance",
            )
        ],
        retrieval_items=[
            RetrievalItem(
                source_id="doc#1",
                content="Relevant passage context.",
                is_useful=True,
                relevance_score=0.9,
            )
        ],
        success=success,
        failure_reason=failure_reason,
        final_quality_score=0.95 if success else 0.6,
        split=split,
        is_verified=True,
        review_status=ReviewStatus.APPROVED,
    )


def test_pipeline_process_records() -> None:
    pipeline = TrainingDataPipeline()

    r1 = _sample_experience("s1", DatasetSplit.TRAIN, success=True)
    r2 = _sample_experience("s2", DatasetSplit.VAL, success=True)
    # Duplicate r1
    r1_dup = _sample_experience("s1", DatasetSplit.TRAIN, success=True)

    clean_ds, val_result = pipeline.process_records([r1, r2, r1_dup])
    assert len(clean_ds) == 2
    assert val_result.duplicate_count == 1


def test_pipeline_export_training_artifacts(tmp_path: Path) -> None:
    pipeline = TrainingDataPipeline(min_quality_score=0.7, require_verified=True, allow_failures=False)

    r_train1 = _sample_experience("t1", DatasetSplit.TRAIN, success=True)
    r_train2 = _sample_experience("t2", DatasetSplit.TRAIN, success=True)
    r_val = _sample_experience("v1", DatasetSplit.VAL, success=True)
    r_failed = _sample_experience("f1", DatasetSplit.TRAIN, success=False)  # Should be filtered out from SFT

    ds = ExperienceDataset([r_train1, r_train2, r_val, r_failed])

    out_dir = tmp_path / "artifacts"
    manifest = pipeline.export_training_artifacts(
        dataset=ds,
        output_dir=out_dir,
        export_sft=True,
        export_dpo=True,
        export_structured=True,
    )

    assert isinstance(manifest, PipelineManifest)
    assert manifest.total_input_records == 4
    assert manifest.training_eligible_records == 3  # Failed record excluded
    assert manifest.sft_examples_exported == 3
    assert manifest.structured_examples_exported == 3
    assert manifest.dpo_pairs_exported == 4  # DPO extracts alternatives from all records

    # Verify generated files exist on disk
    assert (out_dir / "sft_chat.jsonl").is_file()
    assert (out_dir / "dpo_pairs.jsonl").is_file()
    assert (out_dir / "structured_agent.jsonl").is_file()
    assert (out_dir / "pipeline_manifest.json").is_file()
    assert (out_dir / "train.jsonl").is_file()
    assert (out_dir / "val.jsonl").is_file()

    # Verify SFT jsonl can be parsed
    with (out_dir / "sft_chat.jsonl").open("r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 3
    assert "messages" in lines[0]
