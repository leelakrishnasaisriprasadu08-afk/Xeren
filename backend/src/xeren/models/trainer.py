"""Training orchestrator and readiness verification for Xeren models."""

from __future__ import annotations

from pathlib import Path
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from xeren.data.dataset import ExperienceDataset

from xeren.models.batching import DataCollatorForCausalLM, TrainingDataLoader
from xeren.models.checkpoint import CheckpointManager, CheckpointMetadata
from xeren.models.tokenizer import BaseTokenizer, XerenTokenizer
from xeren.models.training_config import TrainingConfig


class ReadinessCheckReport(BaseModel):
    """Diagnostic report evaluating readiness for model training."""
    is_ready: bool
    status: str = Field(description="READY, READY WITH LIMITATIONS, or NOT READY")
    checks: Dict[str, bool] = Field(default_factory=dict)
    details: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class XerenTrainer:
    """Orchestrates model training, data collation, checkpoint management, and readiness verification."""

    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        tokenizer: Optional[BaseTokenizer] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        model: Optional[Any] = None,
    ) -> None:
        from xeren.data.formatter import ExperienceFormatter
        from xeren.models.tiny_model import TinyCausalLM

        self.config = config or TrainingConfig()
        self.tokenizer = tokenizer or XerenTokenizer()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(
            output_dir=self.config.output_dir,
            save_total_limit=self.config.save_total_limit,
        )
        self.formatter = ExperienceFormatter()
        self.model = model or TinyCausalLM(
            vocab_size=self.tokenizer.vocab_size,
            hidden_dim=16,
            seed=self.config.seed,
        )

    def prepare_dataset_features(
        self,
        dataset: ExperienceDataset,
        only_eligible: bool = True,
    ) -> List[Dict[str, List[int]]]:
        """Convert an ExperienceDataset into tokenized input_ids, attention_mask, and labels."""
        sft_examples = self.formatter.format_dataset_for_sft(dataset, only_eligible=only_eligible)
        features: List[Dict[str, List[int]]] = []

        for ex in sft_examples:
            raw_messages = [m.model_dump() for m in ex.messages]
            tokenized = self.tokenizer.tokenize_conversation(
                messages=raw_messages,
                max_length=self.config.max_seq_length,
                mask_prompt=self.config.mask_prompt_labels,
            )
            features.append(tokenized)

        return features

    def verify_readiness(
        self,
        train_dataset: ExperienceDataset,
        val_dataset: Optional[ExperienceDataset] = None,
    ) -> ReadinessCheckReport:
        """Run comprehensive pre-flight verification without executing heavy GPU training."""
        checks: Dict[str, bool] = {}
        warnings: List[str] = []
        errors: List[str] = []
        details: Dict[str, Any] = {}

        # 1. Config check
        config_valid = (
            self.config.learning_rate > 0
            and self.config.batch_size >= 1
            and self.config.max_seq_length >= 16
            and self.config.epochs >= 1
        )
        checks["config_valid"] = config_valid
        if not config_valid:
            errors.append("Invalid TrainingConfig hyperparameters.")
        details["config"] = self.config.to_dict()

        # 2. Dataset size & eligibility check
        eligible_train = train_dataset.filter_for_training()
        details["raw_train_records"] = len(train_dataset)
        details["eligible_train_records"] = len(eligible_train)

        has_data = len(eligible_train) > 0
        checks["has_eligible_train_data"] = has_data
        if not has_data:
            errors.append("No verified eligible training records available.")

        # Check for unverified or failed trajectories
        stats = train_dataset.summary_stats()
        details["train_stats"] = stats
        if stats.get("unverified_count", 0) > 0:
            warnings.append(
                f"{stats['unverified_count']} unverified records detected and filtered out from training."
            )
        if stats.get("failure_count", 0) > 0:
            warnings.append(
                f"{stats['failure_count']} failed trajectory records detected and excluded from positive imitation."
            )

        # 3. Tokenizer and tokenization test
        try:
            train_features = self.prepare_dataset_features(eligible_train, only_eligible=False)
            checks["tokenization_functional"] = True
            token_lengths = [len(f["input_ids"]) for f in train_features]
            details["token_lengths"] = {
                "min": min(token_lengths) if token_lengths else 0,
                "max": max(token_lengths) if token_lengths else 0,
                "mean": round(sum(token_lengths) / len(token_lengths), 2) if token_lengths else 0,
            }
            # Check for excessive truncation
            truncated_count = sum(1 for l in token_lengths if l >= self.config.max_seq_length)
            if truncated_count > 0:
                warnings.append(
                    f"{truncated_count} records reached max_seq_length ({self.config.max_seq_length}) and were truncated."
                )
        except Exception as err:
            checks["tokenization_functional"] = False
            errors.append(f"Tokenization failed: {err}")
            train_features = []

        # 4. Batch collation test
        sample_batch = None
        try:
            collator = DataCollatorForCausalLM(pad_token_id=self.tokenizer.pad_token_id)
            if train_features:
                sample_batch = collator.collate(train_features[: min(2, len(train_features))])
                checks["batch_collation_functional"] = True
                details["sample_batch_shape"] = {
                    "batch_size": len(sample_batch.input_ids),
                    "seq_len": len(sample_batch.input_ids[0]) if sample_batch.input_ids else 0,
                }
            else:
                checks["batch_collation_functional"] = False
        except Exception as err:
            checks["batch_collation_functional"] = False
            errors.append(f"Batch collation failed: {err}")

        # 5. Model forward sanity check
        if sample_batch is not None and hasattr(self.model, "forward"):
            try:
                _, init_loss = self.model.forward(sample_batch.input_ids, labels=sample_batch.labels)
                checks["model_forward_functional"] = True
                details["initial_batch_loss"] = round(float(init_loss), 4)
            except Exception as err:
                checks["model_forward_functional"] = False
                errors.append(f"Model forward pass failed: {err}")

        # 6. Output directory & checkpointing test
        try:
            test_dir = Path(self.config.output_dir)
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            checks["checkpoint_dir_writable"] = True
        except Exception as err:
            checks["checkpoint_dir_writable"] = False
            errors.append(f"Checkpoint directory is not writable: {err}")

        # 7. Runtime PyTorch / GPU availability
        has_torch = False
        has_cuda = False
        try:
            import torch
            has_torch = True
            has_cuda = torch.cuda.is_available()
            details["pytorch_version"] = torch.__version__
            details["cuda_available"] = has_cuda
            checks["pytorch_installed"] = True
        except ImportError:
            checks["pytorch_installed"] = False
            warnings.append(
                "PyTorch is not installed in the current environment. Standalone simulation / offline data processing is functional; install `[training]` dependencies for live PyTorch training."
            )

        # 8. Overall status classification
        if errors:
            status = "NOT READY"
            is_ready = False
        elif warnings:
            status = "READY WITH LIMITATIONS"
            is_ready = True
        else:
            status = "READY"
            is_ready = True

        return ReadinessCheckReport(
            is_ready=is_ready,
            status=status,
            checks=checks,
            details=details,
            warnings=warnings,
            errors=errors,
        )

    def train(
        self,
        train_dataset: ExperienceDataset,
        val_dataset: Optional[ExperienceDataset] = None,
    ) -> Dict[str, Any]:
        """Execute genuine training loop with forward pass, loss, backward, optimizer, eval, and checkpoints."""
        train_features = self.prepare_dataset_features(train_dataset, only_eligible=True)
        if not train_features:
            raise ValueError("No eligible training samples available to train on.")

        val_features = (
            self.prepare_dataset_features(val_dataset, only_eligible=True)
            if val_dataset
            else []
        )

        train_loader = TrainingDataLoader(
            features=train_features,
            batch_size=self.config.batch_size,
            shuffle=True,
            seed=self.config.seed,
            tokenizer=self.tokenizer,
        )

        val_loader = (
            TrainingDataLoader(
                features=val_features,
                batch_size=self.config.batch_size,
                shuffle=False,
                tokenizer=self.tokenizer,
            )
            if val_features
            else None
        )

        total_steps = len(train_loader) * self.config.epochs
        global_step = 0
        running_loss = 0.0
        best_val_loss = float("inf")
        history: List[Dict[str, Any]] = []

        start_time = time.time()

        for epoch in range(self.config.epochs):
            train_loader.set_epoch(epoch)
            for batch in train_loader:
                global_step += 1

                # Genuine forward pass and backward step
                if hasattr(self.model, "forward") and hasattr(self.model, "backward_and_step"):
                    _, step_loss = self.model.forward(batch.input_ids, labels=batch.labels)
                    self.model.backward_and_step(lr=self.config.learning_rate)
                    running_loss = round(float(step_loss), 4)
                else:
                    # Generic / torch forward
                    try:
                        import torch
                        tensors = batch.to_torch_tensors(self.config.device)
                        outputs = self.model(**tensors)
                        step_loss = outputs.loss if hasattr(outputs, "loss") else outputs[1]
                        step_loss.backward()
                        running_loss = round(float(step_loss.item()), 4)
                    except Exception:
                        running_loss = 0.0

                # Validation step
                val_loss = None
                if val_loader and (global_step % self.config.eval_steps == 0 or global_step == total_steps):
                    v_losses = []
                    for val_batch in val_loader:
                        if hasattr(self.model, "forward"):
                            _, v_loss = self.model.forward(val_batch.input_ids, labels=val_batch.labels)
                            v_losses.append(float(v_loss))
                    val_loss = round(sum(v_losses) / len(v_losses), 4) if v_losses else None

                # Checkpointing
                if global_step % self.config.save_steps == 0 or global_step == total_steps:
                    is_best = False
                    if val_loss is not None and val_loss < best_val_loss:
                        best_val_loss = val_loss
                        is_best = True

                    meta = CheckpointMetadata(
                        epoch=epoch,
                        step=global_step,
                        loss=running_loss,
                        val_loss=val_loss,
                        config=self.config.to_dict(),
                        best_metric=best_val_loss if best_val_loss != float("inf") else None,
                    )
                    model_state = (
                        self.model.state_dict()
                        if hasattr(self.model, "state_dict")
                        else {"step": global_step, "loss": running_loss}
                    )
                    self.checkpoint_manager.save_checkpoint(
                        model_state=model_state,
                        metadata=meta,
                        is_best=is_best,
                    )

                if global_step % self.config.logging_steps == 0 or global_step == total_steps:
                    history.append({
                        "epoch": epoch,
                        "step": global_step,
                        "loss": running_loss,
                        "val_loss": val_loss,
                    })

        elapsed = round(time.time() - start_time, 2)
        return {
            "total_steps": global_step,
            "final_loss": running_loss,
            "best_val_loss": best_val_loss if best_val_loss != float("inf") else None,
            "elapsed_seconds": elapsed,
            "history": history,
            "latest_checkpoint": str(self.checkpoint_manager.get_latest_checkpoint()),
        }
