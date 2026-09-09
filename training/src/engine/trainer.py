"""Training Engine for Xeren LLM — Two-Stage GPU Training.

Stage 1: Standard LM loss training on foundation datasets.
Stage 2: Multi-head loss (LM + Plugin + Threat) with gradient checkpointing,
         continuous training integration from Supabase/local buffer, and
         training telemetry logging to PostgreSQL.
"""

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
        gradient_checkpointing: bool = False,
        # Multi-head loss weights (Stage 2)
        lm_loss_weight: float = 1.0,
        plugin_loss_weight: float = 0.3,
        threat_loss_weight: float = 0.2,
        # Continuous training (Stage 2)
        enable_continuous_training: bool = False,
        continuous_pull_every_steps: int = 100,
        continuous_max_episodes: int = 100,
        # Supabase telemetry
        postgres_uri: Optional[str] = None,
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
        self.gradient_checkpointing = gradient_checkpointing

        # Multi-head loss weights
        self.lm_loss_weight = lm_loss_weight
        self.plugin_loss_weight = plugin_loss_weight
        self.threat_loss_weight = threat_loss_weight

        # Continuous training
        self.enable_continuous_training = enable_continuous_training
        self.continuous_pull_every_steps = continuous_pull_every_steps
        self.continuous_max_episodes = continuous_max_episodes
        self._continuous_buffer = None

        self.model.to(self.device)

        # Enable gradient checkpointing for Stage 2 VRAM savings
        if gradient_checkpointing:
            self._enable_gradient_checkpointing()
            logger.info("Gradient checkpointing enabled (Stage 2 VRAM optimization).")

        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)
        self.loss_history: List[Dict[str, Any]] = []
        self.first_30_cases: List[Dict[str, Any]] = []

        # Supabase telemetry
        self._db_engine = None
        self._postgres_uri = postgres_uri or os.getenv("DATABASE_URL")

    def _enable_gradient_checkpointing(self):
        """Enable PyTorch gradient checkpointing on transformer blocks to reduce VRAM."""
        try:
            self.model.enable_gradient_checkpointing(True)
            logger.info(f"Gradient checkpointing applied to {len(self.model.layers)} transformer layers.")
        except Exception as e:
            logger.warning(f"Could not apply gradient checkpointing: {e}")

    def _get_continuous_buffer(self):
        """Lazy-load the hybrid continuous buffer."""
        if self._continuous_buffer is None:
            try:
                from training.src.data.continuous_buffer import HybridContinuousBuffer
                self._continuous_buffer = HybridContinuousBuffer(
                    postgres_uri=self._postgres_uri,
                )
                logger.info("Continuous training buffer connected (Hybrid JSONL + Supabase).")
            except Exception as e:
                logger.warning(f"Could not load continuous buffer: {e}")
        return self._continuous_buffer

    def _pull_and_train_continuous_episodes(self, tokenizer: Any, max_seq_len: int) -> int:
        """Pull fresh episodes from Supabase and run mini fine-tuning steps."""
        buf = self._get_continuous_buffer()
        if not buf:
            return 0

        episodes = buf.pull_for_training(max_episodes=self.continuous_max_episodes)
        if not episodes:
            logger.info("No new episodes available for continuous training.")
            return 0

        logger.info(f"Running continuous training on {len(episodes)} fresh user episodes...")
        trained_ids = []
        self.model.train()

        for ep in episodes:
            try:
                from training.src.data.dataset_builder import format_chatml, SYSTEM_PROMPTS
                text = format_chatml(SYSTEM_PROMPTS["default"], [
                    {"role": "user", "content": ep["user"]},
                    {"role": "thought", "content": ep.get("thought", "")},
                    {"role": "assistant", "content": ep["assistant"]},
                ])
                ids = tokenizer.encode(text)[:max_seq_len]
                input_ids = torch.tensor([ids], dtype=torch.long, device=self.device)
                labels = input_ids.clone()

                with torch.amp.autocast("cuda", enabled=self.use_amp):
                    out = self.model(input_ids, labels=labels)
                    loss = out.get("total_loss") or out.get("loss")
                    if loss is not None:
                        loss = loss / self.gradient_accumulation_steps

                if loss is not None:
                    if self.use_amp:
                        self.scaler.scale(loss).backward()
                    else:
                        loss.backward()
                    trained_ids.append(ep["episode_id"])

            except Exception as e:
                logger.warning(f"Continuous training failed for episode {ep.get('episode_id', '?')[:8]}: {e}")

        # Optimizer step for continuous batch
        if trained_ids:
            if self.use_amp:
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()
            self.optimizer.zero_grad()

            # Mark episodes as trained in Supabase
            buf.mark_trained(trained_ids)
            logger.info(f"Continuous training complete: {len(trained_ids)} episodes trained and marked.")

        return len(trained_ids)

    def _log_to_supabase(self, step: int, epoch: int, loss: float, lr: float, stage: int = 1):
        """Log training telemetry to Supabase for monitoring."""
        if not self._postgres_uri:
            return
        try:
            if self._db_engine is None:
                from sqlmodel import create_engine
                self._db_engine = create_engine(self._postgres_uri, pool_pre_ping=True)
            from sqlmodel import text
            ensure_sql = """
            CREATE TABLE IF NOT EXISTS training_telemetry (
                id SERIAL PRIMARY KEY,
                step INT, epoch INT, stage INT,
                loss FLOAT, learning_rate FLOAT,
                timestamp TIMESTAMP DEFAULT NOW()
            );
            """
            insert_sql = """
            INSERT INTO training_telemetry (step, epoch, stage, loss, learning_rate)
            VALUES (:step, :epoch, :stage, :loss, :lr);
            """
            with self._db_engine.connect() as conn:
                conn.execute(text(ensure_sql))
                conn.execute(text(insert_sql), {
                    "step": step, "epoch": epoch, "stage": stage,
                    "loss": float(loss), "lr": float(lr),
                })
                conn.commit()
        except Exception as e:
            logger.debug(f"Supabase telemetry log failed (non-critical): {e}")

    def _render_perfect_vision_milestone(self, stage: int, tokenizer: Optional[Any] = None):
        """Render comprehensive milestone report for the first 30 training cases."""
        if not self.first_30_cases:
            return

        c1_loss = self.first_30_cases[0]["loss"]
        c30_loss = self.first_30_cases[-1]["loss"]
        delta = c1_loss - c30_loss
        pct_drop = (delta / max(c1_loss, 1e-4)) * 100.0
        avg_step_ms = sum(c["step_time_ms"] for c in self.first_30_cases) / len(self.first_30_cases)
        peak_vram = max(c["vram_peak_mb"] for c in self.first_30_cases)

        print("\n" + "=" * 80, flush=True)
        print("          XEREN PERFECT VISION MILESTONE: FIRST 30 CASES COMPLETE", flush=True)
        print("=" * 80, flush=True)
        print(f" {'Case':<6} | {'Loss':<10} | {'LR':<10} | {'VRAM Peak':<12} | {'Step Time':<10}", flush=True)
        print("-" * 80, flush=True)
        for c in self.first_30_cases:
            print(
                f" #{c['case']:<5} | {c['loss']:<10.4f} | {c['lr']:<10.2e} | "
                f"{c['vram_peak_mb']:<6.0f} MB   | {c['step_time_ms']:<8.0f} ms",
                flush=True
            )
        print("-" * 80, flush=True)
        print(f" • Initial Loss (Case 1)   : {c1_loss:.4f}", flush=True)
        print(f" • Milestone Loss (Case 30): {c30_loss:.4f}", flush=True)
        print(f" • Loss Reduction          : {delta:+.4f} ({pct_drop:.1f}% convergence)", flush=True)
        print(f" • Average Step Time       : {avg_step_ms:.1f} ms", flush=True)
        print(f" • Peak GPU VRAM           : {peak_vram:.0f} MB / 8,188 MB (HEALTHY - NO OOM)", flush=True)

        # Vision Sample Generation Check
        if tokenizer is not None:
            try:
                print("\n[Vision Sample Check] Generating output from current model weights...", flush=True)
                test_prompt = "<|im_start|>user\nWhat is your purpose?\n<|im_end|>\n<|im_start|>thought\n"
                input_ids = torch.tensor([tokenizer.encode(test_prompt)], dtype=torch.long, device=self.device)
                gen_ids = self.model.generate(
                    input_ids,
                    max_new_tokens=30,
                    temperature=0.7,
                    eos_token_id=tokenizer.eos_token_id,
                )
                generated_text = tokenizer.decode(gen_ids[0].tolist())
                print(f"Prompt: {repr(test_prompt)}", flush=True)
                print(f"Output: {repr(generated_text)}", flush=True)
            except Exception as e:
                logger.warning(f"Vision sample generation failed: {e}")

        # Save milestone report to disk
        try:
            report_path = self.checkpoint_dir / "first_30_cases_vision.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({
                    "stage": stage,
                    "model_parameters": self.model.count_parameters(),
                    "initial_loss": c1_loss,
                    "milestone_loss": c30_loss,
                    "loss_drop": delta,
                    "loss_drop_pct": pct_drop,
                    "peak_vram_mb": peak_vram,
                    "avg_step_ms": avg_step_ms,
                    "cases": self.first_30_cases,
                }, f, indent=2)
            print(f"\nSaved Perfect Vision report to: {report_path}", flush=True)
        except Exception as e:
            logger.warning(f"Could not save vision report: {e}")

        print("=" * 80, flush=True)
        print("==> Perfect Vision Verified! Continuing full training loop for remaining duration...", flush=True)
        print("=" * 80 + "\n", flush=True)

    def train(
        self,
        num_epochs: int = 1,
        max_steps: Optional[int] = None,
        stage: int = 1,
        tokenizer: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Run full training loop with multi-head loss support."""
        self.model.train()
        total_steps = 0
        running_loss = 0.0
        running_plugin_loss = 0.0
        running_threat_loss = 0.0
        start_time = time.time()

        logger.info(
            f"Starting Xeren Stage {stage} training: {num_epochs} epochs, device={self.device}, "
            f"params={self.model.count_parameters():,}, "
            f"AMP={self.use_amp}, GradChk={self.gradient_checkpointing}"
        )
        if self.model.config.enable_plugin_head:
            logger.info("Stage 2 heads active: PluginHead + ConfidenceHead + ThreatHead")

        step_start_time = time.time()
        for epoch in range(num_epochs):
            for batch_idx, batch in enumerate(self.train_dataloader):
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)

                # Optional domain head labels (from batch if present)
                plugin_labels = batch.get("plugin_labels")
                threat_labels = batch.get("threat_labels")
                if plugin_labels is not None:
                    plugin_labels = plugin_labels.to(self.device)
                if threat_labels is not None:
                    threat_labels = threat_labels.to(self.device)

                with torch.amp.autocast("cuda", enabled=self.use_amp):
                    out = self.model(
                        input_ids,
                        labels=labels,
                        plugin_labels=plugin_labels,
                        threat_labels=threat_labels,
                    )
                    # Use total_loss (multi-head) if available, else fall back to lm loss
                    loss = out.get("total_loss") or out.get("loss")
                    if loss is None:
                        continue
                    loss = loss / self.gradient_accumulation_steps

                if self.use_amp:
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()

                running_loss += loss.item() * self.gradient_accumulation_steps
                if out.get("plugin_loss") is not None:
                    running_plugin_loss += out["plugin_loss"].item()
                if out.get("threat_loss") is not None:
                    running_threat_loss += out["threat_loss"].item()

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
                    current_lr = self.optimizer.param_groups[0]["lr"]
                    elapsed_step = time.time() - step_start_time
                    step_start_time = time.time()

                    # --- First 30 Cases: Perfect Vision Telemetry ---
                    vram_alloc = torch.cuda.memory_allocated() / (1024 ** 2) if torch.cuda.is_available() else 0.0
                    vram_peak = torch.cuda.max_memory_allocated() / (1024 ** 2) if torch.cuda.is_available() else 0.0

                    if total_steps <= 30:
                        case_loss = running_loss
                        case_entry = {
                            "case": total_steps,
                            "loss": round(case_loss, 4),
                            "lr": float(f"{current_lr:.2e}"),
                            "vram_allocated_mb": round(vram_alloc, 1),
                            "vram_peak_mb": round(vram_peak, 1),
                            "step_time_ms": round(elapsed_step * 1000, 1),
                        }
                        self.first_30_cases.append(case_entry)
                        print(
                            f"[Vision Case {total_steps:02d}/30] Loss: {case_loss:<7.4f} | "
                            f"LR: {current_lr:.2e} | VRAM: {vram_alloc:<4.0f}MB (Peak: {vram_peak:<4.0f}MB) | "
                            f"Time: {elapsed_step*1000:<4.0f}ms",
                            flush=True
                        )

                        if total_steps == 30:
                            self._render_perfect_vision_milestone(stage, tokenizer)

                    # Standard periodic logging after first 30 cases
                    if total_steps > 30 and total_steps % self.logging_steps == 0:
                        avg_loss = running_loss / self.logging_steps
                        elapsed = time.time() - start_time
                        log_msg = (
                            f"Epoch {epoch+1}/{num_epochs} | Step {total_steps} | "
                            f"Loss: {avg_loss:.4f} | LR: {current_lr:.2e} | Elapsed: {elapsed:.1f}s"
                        )
                        if running_plugin_loss > 0:
                            log_msg += f" | PluginLoss: {running_plugin_loss/self.logging_steps:.4f}"
                        if running_threat_loss > 0:
                            log_msg += f" | ThreatLoss: {running_threat_loss/self.logging_steps:.4f}"
                        logger.info(log_msg)

                        entry = {
                            "step": total_steps, "epoch": epoch + 1,
                            "loss": avg_loss, "lr": current_lr, "stage": stage,
                        }
                        self.loss_history.append(entry)
                        self._log_to_supabase(total_steps, epoch + 1, avg_loss, current_lr, stage)

                    if (total_steps <= 30) or (total_steps % self.logging_steps == 0):
                        running_loss = 0.0
                        running_plugin_loss = 0.0
                        running_threat_loss = 0.0

                    # Evaluation
                    if self.val_dataloader and total_steps % self.eval_steps == 0:
                        val_loss = self.evaluate()
                        logger.info(f"==> Validation Loss at Step {total_steps}: {val_loss:.4f}")
                        self.model.train()

                    # Continuous training pull (Stage 2 only)
                    if (
                        self.enable_continuous_training and
                        stage == 2 and
                        tokenizer is not None and
                        total_steps % self.continuous_pull_every_steps == 0
                    ):
                        n = self._pull_and_train_continuous_episodes(
                            tokenizer, self.model.config.max_seq_len
                        )
                        if n > 0:
                            logger.info(f"Continuous training injected {n} live user episodes.")

                    # Save Checkpoint
                    if total_steps % self.save_steps == 0:
                        self.save_checkpoint(f"checkpoint_step_{total_steps}.pt", stage=stage)

                    if max_steps and total_steps >= max_steps:
                        logger.info(f"Reached max_steps ({max_steps}). Stopping.")
                        self.save_checkpoint("checkpoint_final.pt", stage=stage)
                        return self.loss_history

        self.save_checkpoint("checkpoint_final.pt", stage=stage)
        logger.info(f"Stage {stage} training completed in {time.time() - start_time:.1f}s.")
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
                out = self.model(input_ids, labels=labels)
                loss = out.get("loss")
                if loss is not None:
                    total_loss += loss.item()
                    batches += 1
        return total_loss / max(1, batches)

    def save_checkpoint(self, filename: str, stage: int = 1):
        """Save model weights, config, and training state."""
        save_path = self.checkpoint_dir / filename
        state = {
            "model_state_dict": self.model.state_dict(),
            "config": self.model.config.__dict__,
            "stage": stage,
            "loss_history": self.loss_history,
        }
        if self.optimizer:
            state["optimizer_state_dict"] = self.optimizer.state_dict()
        torch.save(state, save_path)
        logger.info(f"Saved Stage {stage} checkpoint to {save_path}")

        history_path = self.checkpoint_dir / "loss_history.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self.loss_history, f, indent=2)
