"""Training Engine for Xeren LLM training from scratch."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from training.src.model.xeren_transformer import XerenTransformer

logger = logging.getLogger("xeren.training.engine")
logging.basicConfig(level=logging.INFO)


class XerenTrainer:
    def __init__(
        self,
        model: XerenTransformer,
        train_dataloader: DataLoader,
        val_dataloader: Optional[DataLoader] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scheduler: Optional[Any] = None,
        device: str = "cpu",
        gradient_accumulation_steps: int = 1,
        max_grad_norm: float = 1.0,
        checkpoint_dir: str = "training/checkpoints",
        logging_steps: int = 10,
        eval_steps: int = 50,
        save_steps: int = 100,
        use_amp: bool = False,
    ):
        self.model = model
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = torch.device(device)
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logging_steps = logging_steps
        self.eval_steps = eval_steps
        self.save_steps = save_steps
        self.use_amp = use_amp and device != "cpu"

        self.model.to(self.device)
        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)
        self.loss_history: List[Dict[str, Any]] = []

    def train(self, num_epochs: int = 1, max_steps: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run full training loop."""
        self.model.train()
        total_steps = 0
        running_loss = 0.0
        start_time = time.time()

        logger.info(
            f"Starting Xeren training: {num_epochs} epochs, device={self.device}, "
            f"trainable params={self.model.count_parameters():,}"
        )

        for epoch in range(num_epochs):
            for batch_idx, batch in enumerate(self.train_dataloader):
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)

                with torch.amp.autocast("cuda", enabled=self.use_amp):
                    logits, loss, _ = self.model(input_ids, labels=labels)
                    loss = loss / self.gradient_accumulation_steps

                if self.use_amp:
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()

                running_loss += loss.item() * self.gradient_accumulation_steps

                # Optimizer step on accumulation boundary
                if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                    if self.use_amp:
                        self.scaler.unscale_(self.optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                        self.scaler.step(self.optimizer)
                        self.scaler.update()
                    else:
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                        self.optimizer.step()

                    if self.scheduler:
                        self.scheduler.step()

                    self.optimizer.zero_grad()
                    total_steps += 1

                    # Logging
                    if total_steps % self.logging_steps == 0:
                        avg_loss = running_loss / self.logging_steps
                        current_lr = self.optimizer.param_groups[0]["lr"]
                        elapsed = time.time() - start_time
                        logger.info(
                            f"Epoch {epoch+1}/{num_epochs} | Step {total_steps} | "
                            f"Loss: {avg_loss:.4f} | LR: {current_lr:.2e} | Elapsed: {elapsed:.1f}s"
                        )
                        self.loss_history.append({
                            "step": total_steps,
                            "epoch": epoch + 1,
                            "loss": avg_loss,
                            "lr": current_lr,
                        })
                        running_loss = 0.0

                    # Evaluation
                    if self.val_dataloader and total_steps % self.eval_steps == 0:
                        val_loss = self.evaluate()
                        logger.info(f"==> Validation Loss at Step {total_steps}: {val_loss:.4f}")
                        self.model.train()

                    # Save Checkpoint
                    if total_steps % self.save_steps == 0:
                        self.save_checkpoint(f"checkpoint_step_{total_steps}.pt")

                    if max_steps and total_steps >= max_steps:
                        logger.info(f"Reached max_steps ({max_steps}). Stopping training.")
                        self.save_checkpoint("checkpoint_final.pt")
                        return self.loss_history

        # Final save
        self.save_checkpoint("checkpoint_final.pt")
        logger.info(f"Training completed in {time.time() - start_time:.1f}s.")
        return self.loss_history

    def evaluate(self) -> float:
        """Compute evaluation loss over validation set."""
        if not self.val_dataloader:
            return 0.0

        self.model.eval()
        total_loss = 0.0
        batches = 0

        with torch.no_grad():
            for batch in self.val_dataloader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)
                _, loss, _ = self.model(input_ids, labels=labels)
                if loss is not None:
                    total_loss += loss.item()
                    batches += 1

        return total_loss / max(1, batches)

    def save_checkpoint(self, filename: str):
        """Save model weights and training state."""
        save_path = self.checkpoint_dir / filename
        state = {
            "model_state_dict": self.model.state_dict(),
            "config": self.model.config.__dict__,
            "loss_history": self.loss_history,
        }
        if self.optimizer:
            state["optimizer_state_dict"] = self.optimizer.state_dict()
        torch.save(state, save_path)
        logger.info(f"Saved checkpoint to {save_path}")

        # Also write loss history JSON
        history_path = self.checkpoint_dir / "loss_history.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self.loss_history, f, indent=2)
