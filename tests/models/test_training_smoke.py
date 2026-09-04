"""Deterministic end-to-end training smoke test for Xeren model learning foundation.

Verifies the complete pipeline:
dataset
-> validation & curation
-> training eligibility
-> formatting (SFT Chat)
-> tokenizer with agent tokens
-> prompt loss masking (-100)
-> batch collation
-> model forward pass
-> causal cross-entropy loss
-> backward pass
-> optimizer step & loss reduction
-> validation loss
-> checkpoint save
-> checkpoint reload & verification.
"""

from pathlib import Path
import pytest

from xeren.data.dataset import load_jsonl_dataset
from xeren.data.formatter import ExperienceFormatter
from xeren.data.schema import ReviewStatus
from xeren.models.batching import DataCollatorForCausalLM, TrainingDataLoader
from xeren.models.checkpoint import CheckpointManager
from xeren.models.tiny_model import TinyCausalLM
from xeren.models.tokenizer import IGNORE_INDEX, XerenTokenizer
from xeren.models.trainer import XerenTrainer
from xeren.models.training_config import TrainingConfig


def test_real_training_smoke_test(tmp_path: Path) -> None:
    """Execute a genuine, deterministic training smoke test verifying every stage of the pipeline."""
    # 1. Dataset loading from committed files
    train_path = Path("data/train.jsonl")
    val_path = Path("data/val.jsonl")
    assert train_path.is_file(), "data/train.jsonl must exist"
    assert val_path.is_file(), "data/val.jsonl must exist"

    train_ds = load_jsonl_dataset(train_path, split="train", enforce_verified=True)
    val_ds = load_jsonl_dataset(val_path, split="val", enforce_verified=True)

    assert len(train_ds) == 3
    assert len(val_ds) == 2

    # 2. Training eligibility & safety: negative trajectory isolation
    eligible_train = train_ds.filter_for_training(require_verified=True, allow_failures=False)
    # exp-train-003 is a failure test; it must be excluded from positive SFT
    assert len(eligible_train) == 2
    assert eligible_train.get("exp-train-003") is None
    assert eligible_train.get("exp-train-001") is not None
    assert eligible_train.get("exp-train-002") is not None

    # 3. Formatting into SFT Chat examples
    formatter = ExperienceFormatter()
    sft_examples = formatter.format_dataset_for_sft(eligible_train)
    assert len(sft_examples) == 2
    for ex in sft_examples:
        roles = [m.role for m in ex.messages]
        assert roles == ["system", "user", "assistant"]

    # 4. Tokenizer & prompt loss masking (-100)
    tokenizer = XerenTokenizer()
    features = []
    for ex in sft_examples:
        raw_msgs = [m.model_dump() for m in ex.messages]
        tok_res = tokenizer.tokenize_conversation(raw_msgs, mask_prompt=True)
        features.append(tok_res)

        # Verify system and user tokens have label -100
        labels = tok_res["labels"]
        assert IGNORE_INDEX in labels, "Prompt tokens must be masked with -100"
        # Verify assistant tokens have real label IDs
        unmasked = [l for l in labels if l != IGNORE_INDEX]
        assert len(unmasked) > 0, "Assistant response tokens must have valid labels"

    # 5. Batching & collation
    collator = DataCollatorForCausalLM(pad_token_id=tokenizer.pad_token_id)
    batch = collator.collate(features)
    assert len(batch.input_ids) == 2
    assert len(batch.input_ids[0]) == len(batch.input_ids[1])
    assert len(batch.labels[0]) == len(batch.labels[1])

    # 6. Model initialization
    model = TinyCausalLM(
        vocab_size=tokenizer.vocab_size,
        hidden_dim=16,
        seed=42,
    )

    # 7. Forward pass & genuine initial loss
    _, initial_loss = model.forward(batch.input_ids, labels=batch.labels)
    assert initial_loss > 0.0, "Initial cross-entropy loss must be positive"

    # 8. Backward pass & optimizer step
    model.backward_and_step(lr=0.1)

    # 9. Forward pass 2: Verify loss strictly decreases
    _, post_step_loss = model.forward(batch.input_ids, labels=batch.labels)
    assert post_step_loss < initial_loss, (
        f"Loss must decrease after gradient descent step: initial {initial_loss:.4f} -> post {post_step_loss:.4f}"
    )

    # 10. End-to-end Trainer execution with validation & checkpointing
    ckpt_dir = tmp_path / "smoke_checkpoints"
    config = TrainingConfig(
        output_dir=str(ckpt_dir),
        epochs=3,
        batch_size=2,
        learning_rate=0.05,
        eval_steps=1,
        save_steps=1,
        logging_steps=1,
        max_seq_length=64,
        seed=42,
    )

    trainer = XerenTrainer(
        config=config,
        tokenizer=tokenizer,
        model=model,
    )

    # Pre-flight readiness check
    readiness = trainer.verify_readiness(train_ds, val_ds)
    assert readiness.is_ready is True
    assert readiness.checks["config_valid"] is True
    assert readiness.checks["has_eligible_train_data"] is True
    assert readiness.checks["tokenization_functional"] is True
    assert readiness.checks["batch_collation_functional"] is True
    assert readiness.checks["model_forward_functional"] is True

    # Run genuine training loop
    result = trainer.train(train_ds, val_ds)
    assert result["total_steps"] == 3  # 1 batch * 3 epochs
    assert result["final_loss"] < initial_loss
    assert result["best_val_loss"] is not None

    # 11. Checkpoint save & reload verification
    latest_ckpt_path = trainer.checkpoint_manager.get_latest_checkpoint()
    assert latest_ckpt_path is not None
    assert (latest_ckpt_path / "metadata.json").is_file()
    assert (latest_ckpt_path / "model_state.json").is_file()

    # Create a fresh model and restore state
    fresh_model = TinyCausalLM(
        vocab_size=tokenizer.vocab_size,
        hidden_dim=16,
        seed=999,  # Different initial weights
    )
    # Before restore, fresh model produces different loss
    _, fresh_loss = fresh_model.forward(batch.input_ids, labels=batch.labels)
    assert abs(fresh_loss - initial_loss) > 0.01

    # Reload checkpoint
    saved_state, meta = trainer.checkpoint_manager.load_checkpoint(latest_ckpt_path)
    fresh_model.load_state_dict(saved_state)

    # After restore, fresh model produces identical loss to original trained model
    _, model_end_loss = model.forward(batch.input_ids, labels=batch.labels)
    _, restored_loss = fresh_model.forward(batch.input_ids, labels=batch.labels)
    assert round(restored_loss, 4) == round(model_end_loss, 4)
    assert meta.step == result["total_steps"]


def test_training_safety_rules() -> None:
    """Verify safety gates: rejection of contradictions, unverified records, and split leakage."""
    train_path = Path("data/train.jsonl")
    train_ds = load_jsonl_dataset(train_path, split="train", enforce_verified=True)

    # 1. Negative trajectory isolation
    failed_record = train_ds.get("exp-train-003")
    assert failed_record is not None
    assert failed_record.success is False
    assert failed_record.failure_reason is not None

    ok, reason = failed_record.is_training_eligible(allow_failures=False)
    assert ok is False
    assert "failed trajectory" in reason

    # 2. Contradiction: marked success=True with failure_reason
    contra_rec = failed_record.model_copy(update={"success": True})
    ok, reason = contra_rec.is_training_eligible()
    assert ok is False
    assert "claims success=True but provides failure_reason" in reason

    # 3. Contradiction: marked success=False without failure_reason
    contra_rec2 = failed_record.model_copy(update={"failure_reason": None})
    ok, reason = contra_rec2.is_training_eligible(allow_failures=True)
    assert ok is False
    assert "missing failure_reason" in reason

    # 4. Contradiction: success=True but verification failed
    contra_rec3 = failed_record.model_copy(update={
        "success": True,
        "failure_reason": None,
        "verification": failed_record.verification.model_copy(update={"verified": False}),
    })
    ok, reason = contra_rec3.is_training_eligible()
    assert ok is False
    assert "verification.verified is False" in reason

    # 5. Rejected curation status
    rejected_rec = failed_record.model_copy(update={"review_status": ReviewStatus.REJECTED})
    ok, reason = rejected_rec.is_training_eligible()
    assert ok is False
    assert "rejected" in reason
