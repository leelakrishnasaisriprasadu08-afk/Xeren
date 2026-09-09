"""Path B Matured Alignment Fine-Tuning for Xeren 214M LLM.

Fine-tunes the Stage-1 checkpoint (checkpoint_final.pt) on the 1,600-sample
9-pillar alignment dataset using:
- Assistant-token loss masking (labels = -100 on system & user prompt tokens)
- Micro-batch size 2, gradient accumulation 8 (effective batch size 16)
- FP16 Automatic Mixed Precision (AMP) with gradient checkpointing
- Cosine learning rate schedule with linear warmup (peak LR = 2.5e-5)
- Gradient clipping at 1.0
- Deterministic seed 42
- Full telemetry: peak VRAM, throughput (tokens/sec), train loss, val loss
- Safe resume support from intermediate checkpoints
- Preserves base Stage-1 checkpoint; writes exclusively to stage1_matured/
"""

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.src.engine.optimizer import build_optimizer, get_cosine_schedule_with_warmup
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("matured_alignment")


def set_seed(seed: int = 42) -> None:
    """Set deterministic seeds across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


class MaturedAlignmentDataset(Dataset):
    """PyTorch Dataset with assistant-token loss masking for ChatML."""

    def __init__(
        self,
        texts: List[str],
        tokenizer: XerenTokenizer,
        max_seq_len: int = 512,
    ):
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.samples: List[Dict[str, torch.Tensor]] = []
        self._tokenize_and_mask_all(texts)

    def _tokenize_and_mask_all(self, texts: List[str]) -> None:
        """Pre-tokenize and compute assistant loss masks in memory."""
        assistant_prefix = self.tokenizer._tokenizer.encode("<|im_start|>assistant\n").ids
        im_end_id = self.tokenizer._tokenizer.token_to_id("<|im_end|>")
        eos_id = self.tokenizer.eos_token_id
        pad_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0

        for text in texts:
            token_ids = self.tokenizer.encode(text, add_special_tokens=True)
            if eos_id is not None and (not token_ids or token_ids[-1] != eos_id):
                token_ids.append(eos_id)

            if len(token_ids) > self.max_seq_len:
                token_ids = token_ids[: self.max_seq_len]

            seq_len = len(token_ids)
            labels = [-100] * seq_len

            # Scan and mask: only tokens within assistant turns receive actual token_ids
            prefix_len = len(assistant_prefix)
            i = 0
            while i <= seq_len - prefix_len:
                if token_ids[i : i + prefix_len] == assistant_prefix:
                    start_idx = i + prefix_len
                    end_idx = start_idx
                    while end_idx < seq_len and token_ids[end_idx] != im_end_id:
                        end_idx += 1
                    # Include <|im_end|>
                    if end_idx < seq_len:
                        end_idx += 1
                    # Include trailing newline if present
                    if end_idx < seq_len and token_ids[end_idx] == 211:
                        end_idx += 1
                    # Include EOS token if at end of turn
                    if end_idx < seq_len and token_ids[end_idx] == eos_id:
                        end_idx += 1

                    for j in range(start_idx, end_idx):
                        labels[j] = token_ids[j]
                    i = end_idx
                else:
                    i += 1

            pad_len = self.max_seq_len - seq_len
            input_ids = token_ids + [pad_id] * pad_len
            labels = labels + [-100] * pad_len
            attention_mask = [1] * seq_len + [0] * pad_len

            self.samples.append(
                {
                    "input_ids": torch.tensor(input_ids, dtype=torch.long),
                    "labels": torch.tensor(labels, dtype=torch.long),
                    "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
                }
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        return self.samples[index]


def evaluate_validation_loss(
    model: XerenTransformer,
    val_loader: DataLoader,
    device: torch.device,
    use_amp: bool = True,
) -> float:
    """Compute cross-entropy loss over validation dataset."""
    model.eval()
    total_loss = 0.0
    total_batches = 0

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)

            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                out = model(input_ids, labels=labels)
                loss = out.get("loss")
                if loss is not None and not torch.isnan(loss):
                    total_loss += loss.item()
                    total_batches += 1

    model.train()
    return total_loss / max(1, total_batches)


def run_alignment(args: argparse.Namespace) -> Dict[str, Any]:
    """Execute Matured Alignment fine-tuning with full telemetry."""
    set_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.force_cpu else "cpu")
    logger.info(f"Target Compute Device: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    # 1. Load Tokenizer
    tokenizer_path = Path(args.tokenizer_path)
    if not tokenizer_path.exists():
        raise FileNotFoundError(f"Tokenizer directory not found: {tokenizer_path}")
    logger.info(f"Loading Xeren 32K Tokenizer from: {tokenizer_path}")
    tokenizer = XerenTokenizer.load(str(tokenizer_path))

    # 2. Load Dataset
    train_path = Path(args.train_data)
    val_path = Path(args.val_data)
    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError(f"Dataset files not found: {train_path} or {val_path}")

    logger.info(f"Loading train data from: {train_path}")
    with open(train_path, "r", encoding="utf-8") as f:
        train_texts = json.load(f)
    logger.info(f"Loading validation data from: {val_path}")
    with open(val_path, "r", encoding="utf-8") as f:
        val_texts = json.load(f)

    logger.info(f"Tokenizing & applying assistant loss masking to {len(train_texts)} train and {len(val_texts)} val samples...")
    t_data_start = time.time()
    train_dataset = MaturedAlignmentDataset(train_texts, tokenizer, max_seq_len=args.max_seq_len)
    val_dataset = MaturedAlignmentDataset(val_texts, tokenizer, max_seq_len=args.max_seq_len)
    logger.info(f"Dataset pre-tokenization complete in {time.time() - t_data_start:.2f}s.")

    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.micro_batch_size,
        shuffle=True,
        generator=generator,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.micro_batch_size,
        shuffle=False,
        drop_last=False,
    )

    # 3. Load Model from Base Checkpoint
    base_ckpt_path = Path(args.base_checkpoint)
    if not base_ckpt_path.exists():
        raise FileNotFoundError(f"Base checkpoint not found at: {base_ckpt_path}")

    logger.info(f"Loading Stage-1 base checkpoint from: {base_ckpt_path}")
    ckpt = torch.load(str(base_ckpt_path), map_location=device)
    config = XerenConfig(**ckpt["config"])

    model = XerenTransformer(config).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    logger.info(f"Loaded Xeren 214M model ({model.count_parameters():,} trainable parameters).")

    # Enable gradient checkpointing for VRAM conservation
    if args.gradient_checkpointing:
        model.enable_gradient_checkpointing(True)
        logger.info("Gradient checkpointing enabled.")

    # 4. Build Optimizer, Scaler, and Cosine Scheduler
    optimizer = build_optimizer(
        model,
        learning_rate=args.lr,
        weight_decay=0.01,
        betas=(0.9, 0.95),
        eps=1e-8,
    )

    use_amp = (device.type == "cuda") and args.use_amp
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    # Calculate steps
    steps_per_epoch = math.ceil(len(train_loader) / args.gradient_accumulation_steps)
    total_planned_steps = min(args.max_steps, args.epochs * steps_per_epoch)
    warmup_steps = max(5, int(0.10 * total_planned_steps))

    scheduler = get_cosine_schedule_with_warmup(
        optimizer=optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_planned_steps,
        min_lr_ratio=0.10,
    )

    logger.info(
        f"Training schedule: {args.epochs} planned epochs, {steps_per_epoch} steps/epoch. "
        f"Pilot max steps = {total_planned_steps} (warmup = {warmup_steps} steps, min LR ratio = 0.10)."
    )

    # 5. Handle Safe Resume
    start_epoch = 0
    start_step = 0
    total_tokens_processed = 0
    resume_path = output_dir / "checkpoint_latest.pt"

    if args.resume and resume_path.exists():
        logger.info(f"Resuming training from: {resume_path}")
        r_ckpt = torch.load(str(resume_path), map_location=device)
        model.load_state_dict(r_ckpt["model_state_dict"])
        if "optimizer_state_dict" in r_ckpt:
            optimizer.load_state_dict(r_ckpt["optimizer_state_dict"])
        if "scheduler_state_dict" in r_ckpt:
            scheduler.load_state_dict(r_ckpt["scheduler_state_dict"])
        if "scaler_state_dict" in r_ckpt:
            scaler.load_state_dict(r_ckpt["scaler_state_dict"])
        start_step = r_ckpt.get("step", 0)
        start_epoch = r_ckpt.get("epoch", 0)
        total_tokens_processed = r_ckpt.get("total_tokens_processed", 0)
        logger.info(f"Successfully resumed at Step {start_step}, Epoch {start_epoch}.")

    # 6. Baseline Validation Evaluation (Step 0)
    logger.info("Computing initial baseline validation loss on matured alignment validation set...")
    initial_val_loss = evaluate_validation_loss(model, val_loader, device, use_amp=use_amp)
    logger.info(f"Baseline Validation Loss (Step 0): {initial_val_loss:.4f}")

    # 7. Training Loop
    model.train()
    total_steps = start_step
    running_loss = 0.0
    accumulated_loss = 0.0
    step_start_time = time.time()
    train_start_time = time.time()

    loss_history: List[Dict[str, Any]] = []
    current_val_loss = initial_val_loss

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    logger.info("=================================================================")
    logger.info("STARTING PILOT ALIGNMENT RUN")
    logger.info(f"Micro-batch: {args.micro_batch_size} | Accumulation: {args.gradient_accumulation_steps} | Effective Batch: {args.micro_batch_size * args.gradient_accumulation_steps}")
    logger.info(f"Initial LR: {args.lr:.2e} | Target Max Steps: {total_planned_steps}")
    logger.info("=================================================================")

    stop_training = False
    for epoch in range(start_epoch, args.epochs):
        if stop_training:
            break

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)
            non_pad_tokens = int(batch["attention_mask"].sum().item())
            total_tokens_processed += non_pad_tokens

            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                out = model(input_ids, labels=labels)
                loss = out["loss"]
                if loss is None or not isinstance(loss, torch.Tensor) or torch.isnan(loss):
                    logger.warning("Encountered NaN or invalid loss! Skipping batch.")
                    continue
                loss = loss / args.gradient_accumulation_steps

            if use_amp:
                scaled_loss = scaler.scale(loss)
                assert isinstance(scaled_loss, torch.Tensor)
                scaled_loss.backward()
            else:
                loss.backward()

            accumulated_loss += loss.item() * args.gradient_accumulation_steps

            # Optimization step on gradient accumulation boundary
            if (batch_idx + 1) % args.gradient_accumulation_steps == 0 or (batch_idx + 1) == len(train_loader):
                if use_amp:
                    scaler.unscale_(optimizer)
                    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                    optimizer.step()

                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

                total_steps += 1
                running_loss = accumulated_loss
                accumulated_loss = 0.0

                step_elapsed = time.time() - step_start_time
                step_start_time = time.time()
                current_lr = optimizer.param_groups[0]["lr"]

                vram_allocated = torch.cuda.memory_allocated() / (1024 ** 2) if device.type == "cuda" else 0.0
                vram_peak = torch.cuda.max_memory_allocated() / (1024 ** 2) if device.type == "cuda" else 0.0
                effective_batch_tokens = non_pad_tokens * args.gradient_accumulation_steps
                step_tokens_per_sec = effective_batch_tokens / max(1e-5, step_elapsed)

                # Periodic Logging
                if total_steps % args.logging_steps == 0 or total_steps == 1:
                    logger.info(
                        f"Step {total_steps:03d}/{total_planned_steps:03d} (Epoch {epoch+1}) | "
                        f"Loss: {running_loss:.4f} | LR: {current_lr:.2e} | "
                        f"VRAM: {vram_allocated:.0f}MB (Peak: {vram_peak:.0f}MB) | "
                        f"Throughput: {step_tokens_per_sec:,.0f} tok/s | Time: {step_elapsed*1000:.0f}ms"
                    )

                # Evaluation interval
                if total_steps % args.eval_steps == 0:
                    current_val_loss = evaluate_validation_loss(model, val_loader, device, use_amp=use_amp)
                    logger.info(
                        f"--> [EVAL] Step {total_steps:03d} | Val Loss: {current_val_loss:.4f} "
                        f"(vs Baseline: {initial_val_loss:.4f} | Δ: {current_val_loss - initial_val_loss:+.4f})"
                    )

                # Periodic checkpointing
                if total_steps % args.save_steps == 0:
                    latest_ckpt = {
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "scheduler_state_dict": scheduler.state_dict(),
                        "scaler_state_dict": scaler.state_dict(),
                        "step": total_steps,
                        "epoch": epoch,
                        "config": config.__dict__,
                        "train_loss": running_loss,
                        "val_loss": current_val_loss,
                        "total_tokens_processed": total_tokens_processed,
                        "peak_vram_mb": vram_peak,
                    }
                    torch.save(latest_ckpt, output_dir / "checkpoint_latest.pt")
                    logger.info(f"Saved latest resume checkpoint to: {output_dir / 'checkpoint_latest.pt'}")

                loss_history.append({
                    "step": total_steps,
                    "epoch": epoch,
                    "train_loss": round(running_loss, 4),
                    "val_loss": round(current_val_loss, 4),
                    "lr": float(f"{current_lr:.2e}"),
                    "tokens_per_sec": round(step_tokens_per_sec, 1),
                })

                if total_steps >= total_planned_steps:
                    logger.info(f"Target pilot steps ({total_planned_steps}) reached. Terminating pilot training.")
                    stop_training = True
                    break

    # 8. Final Validation Evaluation
    logger.info("Running final validation evaluation across entire validation set...")
    final_val_loss = evaluate_validation_loss(model, val_loader, device, use_amp=use_amp)
    logger.info(f"Final Validation Loss: {final_val_loss:.4f} (Baseline: {initial_val_loss:.4f})")

    # 9. Save Checkpoint (Pilot & Final)
    total_elapsed_time = time.time() - train_start_time
    peak_vram_final = torch.cuda.max_memory_allocated() / (1024 ** 2) if device.type == "cuda" else 0.0
    overall_throughput = total_tokens_processed / max(1e-5, total_elapsed_time)

    pilot_checkpoint_path = output_dir / "checkpoint_pilot.pt"
    final_checkpoint_path = output_dir / "checkpoint_final.pt"

    checkpoint_data = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "scaler_state_dict": scaler.state_dict(),
        "step": total_steps,
        "epoch": epoch,
        "config": config.__dict__,
        "train_loss": running_loss,
        "val_loss": final_val_loss,
        "initial_val_loss": initial_val_loss,
        "total_tokens_processed": total_tokens_processed,
        "peak_vram_mb": peak_vram_final,
        "total_elapsed_seconds": total_elapsed_time,
        "stage": "matured_alignment_pilot",
    }

    torch.save(checkpoint_data, pilot_checkpoint_path)
    torch.save(checkpoint_data, final_checkpoint_path)
    logger.info(f"Saved pilot checkpoint to: {pilot_checkpoint_path}")
    logger.info(f"Saved final checkpoint to: {final_checkpoint_path}")

    # 10. Generate and Save Machine-Readable Report
    final_lr = optimizer.param_groups[0]["lr"]
    report_data = {
        "task": "Xeren 214M Path B Matured Alignment Pilot",
        "base_checkpoint": str(base_ckpt_path),
        "saved_checkpoint": str(pilot_checkpoint_path),
        "steps_completed": total_steps,
        "epochs_completed": round(total_steps / steps_per_epoch, 2),
        "train_loss": round(running_loss, 4),
        "initial_val_loss": round(initial_val_loss, 4),
        "final_val_loss": round(final_val_loss, 4),
        "val_loss_delta": round(final_val_loss - initial_val_loss, 4),
        "final_learning_rate": float(f"{final_lr:.2e}"),
        "tokens_processed": total_tokens_processed,
        "peak_vram_mb": round(peak_vram_final, 1),
        "overall_throughput_tok_per_sec": round(overall_throughput, 1),
        "total_elapsed_seconds": round(total_elapsed_time, 2),
        "loss_history": loss_history,
    }

    report_path = output_dir / "pilot_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    logger.info(f"Saved telemetry and pilot report to: {report_path}")

    # Print Final Summary Table
    print("\n" + "=" * 70)
    print("XEREN 214M PATH B: PILOT ALIGNMENT RUN COMPLETE")
    print("=" * 70)
    print(f"Training Loss          : {report_data['train_loss']:.4f}")
    print(f"Validation Loss        : {report_data['final_val_loss']:.4f} (Baseline: {report_data['initial_val_loss']:.4f})")
    print(f"Validation Loss Delta  : {report_data['val_loss_delta']:+.4f}")
    print(f"Final Learning Rate    : {report_data['final_learning_rate']:.2e}")
    print(f"Steps Completed        : {report_data['steps_completed']} ({report_data['epochs_completed']} epochs)")
    print(f"Total Tokens Processed : {report_data['tokens_processed']:,}")
    print(f"Peak VRAM              : {report_data['peak_vram_mb']:.1f} MB")
    print(f"Overall Throughput     : {report_data['overall_throughput_tok_per_sec']:,.1f} tokens/second")
    print(f"Checkpoint Path        : {report_data['saved_checkpoint']}")
    print("=" * 70 + "\n")

    return report_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Matured Alignment Fine-Tuning for Xeren 214M.")
    parser.add_argument(
        "--base_checkpoint",
        type=str,
        default="training/checkpoints/stage1/checkpoint_final.pt",
        help="Path to starting Stage-1 checkpoint",
    )
    parser.add_argument(
        "--train_data",
        type=str,
        default="training/data/processed/matured_alignment_train.json",
        help="Path to training samples JSON",
    )
    parser.add_argument(
        "--val_data",
        type=str,
        default="training/data/processed/matured_alignment_val.json",
        help="Path to validation samples JSON",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="training/checkpoints/stage1_matured",
        help="Directory to save aligned checkpoints",
    )
    parser.add_argument(
        "--tokenizer_path",
        type=str,
        default="training/checkpoints/tokenizer_32k",
        help="Path to trained 32K tokenizer directory",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Max number of epochs")
    parser.add_argument("--max_steps", type=int, default=110, help="Max optimizer steps for short pilot")
    parser.add_argument("--micro_batch_size", type=int, default=2, help="Per-device micro-batch size")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2.5e-5, help="Peak learning rate")
    parser.add_argument("--max_grad_norm", type=float, default=1.0, help="Maximum gradient clipping norm")
    parser.add_argument("--max_seq_len", type=int, default=512, help="Maximum context length")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--logging_steps", type=int, default=10, help="Frequency of training log output")
    parser.add_argument("--eval_steps", type=int, default=25, help="Frequency of evaluation on validation set")
    parser.add_argument("--save_steps", type=int, default=50, help="Frequency of intermediate checkpoint saves")
    parser.add_argument("--use_amp", action="store_true", default=True, help="Use FP16 Automatic Mixed Precision")
    parser.add_argument("--gradient_checkpointing", action="store_true", default=True, help="Enable gradient checkpointing")
    parser.add_argument("--resume", action="store_true", default=False, help="Resume training if checkpoint exists")
    parser.add_argument("--force_cpu", action="store_true", default=False, help="Force execution on CPU")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_alignment(args)
