"""Unit and integration tests for Xeren model-training foundation.

Tests TrainingConfig, XerenTokenizer, CheckpointManager,
DataCollatorForCausalLM, TrainingDataLoader, and XerenTrainer.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import (
    ActionStep,
    DatasetSplit,
    ExperienceRecord,
    ReviewStatus,
    VerificationDetails,
)
from xeren.models.batching import (
    Batch,
    DataCollatorForCausalLM,
    TrainingDataLoader,
)
from xeren.models.checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
)
from xeren.models.tokenizer import (
    IGNORE_INDEX,
    SPECIAL_TOKENS,
    TokenizerConfig,
    XerenTokenizer,
)
from xeren.models.trainer import ReadinessCheckReport, XerenTrainer
from xeren.models.training_config import TrainingConfig


def _create_sample_experience(sample_id: str = "train-rec-01") -> ExperienceRecord:
    return ExperienceRecord(
        sample_id=sample_id,
        task=f"Task {sample_id}: Retrieve memory architecture and run calculator",
        plan=["Retrieve docs", "Calculate values"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Retrieve docs",
                tool_name="rag_search",
                tool_args={"query": f"memory_{sample_id}"},
                result=f"Found memory spec for {sample_id}",
                success=True,
            ),
            ActionStep(
                step_index=1,
                plan_step="Calculate values",
                tool_name="calculator",
                tool_args={"expression": "128 * 2"},
                result="256",
                success=True,
            ),
        ],
        prediction_confidence=0.95,
        verification=VerificationDetails(
            verified=True,
            verifier="test_judge",
            score=0.98,
        ),
        success=True,
        final_quality_score=0.96,
        split=DatasetSplit.TRAIN,
        is_verified=True,
        review_status=ReviewStatus.APPROVED,
    )


# ---------------------------------------------------------------------------
# TrainingConfig Tests
# ---------------------------------------------------------------------------

def test_training_config_defaults_and_validation() -> None:
    cfg = TrainingConfig()
    assert cfg.epochs == 3
    assert cfg.batch_size == 4
    assert cfg.gradient_accumulation_steps == 4
    assert cfg.effective_batch_size == 16
    assert cfg.learning_rate == 2e-5

    # Invalid learning rate
    with pytest.raises(ValidationError):
        TrainingConfig(learning_rate=-0.01)

    # Invalid batch size
    with pytest.raises(ValidationError):
        TrainingConfig(batch_size=0)

    # Invalid epochs
    with pytest.raises(ValidationError):
        TrainingConfig(epochs=0)


# ---------------------------------------------------------------------------
# Tokenizer Tests
# ---------------------------------------------------------------------------

def test_xeren_tokenizer_encoding_and_special_tokens() -> None:
    tokenizer = XerenTokenizer()
    assert tokenizer.pad_token_id is not None
    assert tokenizer.eos_token_id is not None
    assert tokenizer.bos_token_id is not None
    assert tokenizer.vocab_size > 256

    text = "Hello Xeren agent <|plan|> Test step <|im_end|>"
    encoded = tokenizer.encode(text, add_special_tokens=True)
    assert len(encoded) > 0
    assert encoded[0] == tokenizer.bos_token_id
    assert encoded[-1] == tokenizer.eos_token_id

    decoded = tokenizer.decode(encoded, skip_special_tokens=False)
    assert "<|plan|>" in decoded
    assert "<|im_end|>" in decoded


def test_xeren_tokenizer_conversation_masking() -> None:
    tokenizer = XerenTokenizer()
    messages = [
        {"role": "system", "content": "You are Xeren."},
        {"role": "user", "content": "Calculate 2+2."},
        {"role": "assistant", "content": "The answer is 4."},
    ]

    features = tokenizer.tokenize_conversation(messages, mask_prompt=True)
    input_ids = features["input_ids"]
    attention_mask = features["attention_mask"]
    labels = features["labels"]

    assert len(input_ids) == len(attention_mask) == len(labels)
    assert all(m == 1 for m in attention_mask)

    # The prompt part (system and user) must be masked with IGNORE_INDEX (-100)
    assert IGNORE_INDEX in labels
    # The assistant generation tokens must NOT be masked with -100
    unmasked_labels = [l for l in labels if l != IGNORE_INDEX]
    assert len(unmasked_labels) > 0


# ---------------------------------------------------------------------------
# CheckpointManager Tests
# ---------------------------------------------------------------------------

def test_checkpoint_manager_save_load_and_prune(tmp_path: Path) -> None:
    ckpt_dir = tmp_path / "checkpoints"
    manager = CheckpointManager(output_dir=ckpt_dir, save_total_limit=2)

    # Save 3 checkpoints
    for step in [10, 20, 30]:
        meta = CheckpointMetadata(
            epoch=1,
            step=step,
            loss=1.0 / step,
            val_loss=0.5,
            config={"step": step},
            best_metric=0.5 if step == 20 else None,
        )
        manager.save_checkpoint(
            model_state={"weights": f"weights-{step}"},
            metadata=meta,
            is_best=(step == 20),
        )

    # Retention limit was 2, so checkpoint-10 must be pruned
    ckpts = manager.list_checkpoints()
    assert len(ckpts) == 2
    ckpt_names = [p.name for p in ckpts]
    assert "checkpoint-10" not in ckpt_names
    assert "checkpoint-20" in ckpt_names
    assert "checkpoint-30" in ckpt_names

    # Check latest and best
    latest = manager.get_latest_checkpoint()
    assert latest is not None
    assert latest.name == "checkpoint-30"

    best = manager.get_best_checkpoint()
    assert best is not None
    assert best.name == "best_checkpoint"

    # Load checkpoint
    state, loaded_meta = manager.load_checkpoint(latest)
    assert state == {"weights": "weights-30"}
    assert loaded_meta.step == 30


# ---------------------------------------------------------------------------
# Batching and DataCollator Tests
# ---------------------------------------------------------------------------

def test_data_collator_dynamic_padding() -> None:
    pad_id = 0
    collator = DataCollatorForCausalLM(pad_token_id=pad_id)

    features = [
        {"input_ids": [10, 20, 30], "attention_mask": [1, 1, 1], "labels": [-100, -100, 30]},
        {"input_ids": [10, 20, 30, 40, 50], "attention_mask": [1, 1, 1, 1, 1], "labels": [-100, -100, 30, 40, 50]},
    ]

    batch = collator.collate(features)
    assert isinstance(batch, Batch)
    assert len(batch.input_ids) == 2
    # Both padded to length 5
    assert len(batch.input_ids[0]) == 5
    assert len(batch.input_ids[1]) == 5

    # First item was padded with pad_id
    assert batch.input_ids[0] == [10, 20, 30, pad_id, pad_id]
    assert batch.attention_mask[0] == [1, 1, 1, 0, 0]
    assert batch.labels[0] == [-100, -100, 30, IGNORE_INDEX, IGNORE_INDEX]


def test_training_dataloader_iteration() -> None:
    features = [
        {"input_ids": [i, i + 1], "attention_mask": [1, 1], "labels": [i, i + 1]}
        for i in range(10)
    ]

    loader = TrainingDataLoader(features=features, batch_size=4, shuffle=True, seed=42)
    assert len(loader) == 3

    batches = list(loader)
    assert len(batches) == 3
    assert len(batches[0].input_ids) == 4
    assert len(batches[1].input_ids) == 4
    assert len(batches[2].input_ids) == 2


# ---------------------------------------------------------------------------
# XerenTrainer Readiness & Training Tests
# ---------------------------------------------------------------------------

def test_trainer_verify_readiness_and_train(tmp_path: Path) -> None:
    out_dir = tmp_path / "trainer_out"
    config = TrainingConfig(
        output_dir=str(out_dir),
        epochs=2,
        batch_size=2,
        eval_steps=1,
        save_steps=2,
        logging_steps=1,
        seed=42,
    )

    trainer = XerenTrainer(config=config)

    train_ds = ExperienceDataset([
        _create_sample_experience("tr-01"),
        _create_sample_experience("tr-02"),
        _create_sample_experience("tr-03"),
    ])
    val_ds = ExperienceDataset([
        _create_sample_experience("vl-01"),
    ])

    # 1. Verify readiness
    report = trainer.verify_readiness(train_ds, val_ds)
    assert isinstance(report, ReadinessCheckReport)
    assert report.is_ready is True
    assert report.checks["config_valid"] is True
    assert report.checks["has_eligible_train_data"] is True
    assert report.checks["tokenization_functional"] is True
    assert report.checks["batch_collation_functional"] is True
    assert report.checks["checkpoint_dir_writable"] is True

    # 2. Run trainer train loop
    train_result = trainer.train(train_ds, val_ds)
    assert train_result["total_steps"] > 0
    assert "final_loss" in train_result
    assert len(train_result["history"]) > 0

    # Checkpoint was written
    latest_ckpt = trainer.checkpoint_manager.get_latest_checkpoint()
    assert latest_ckpt is not None
    assert latest_ckpt.is_dir()
    assert (latest_ckpt / "metadata.json").is_file()
