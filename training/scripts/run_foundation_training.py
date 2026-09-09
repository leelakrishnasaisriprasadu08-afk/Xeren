#!/usr/bin/env python3
"""
Xeren 214M Foundation Continuous Pretraining Engine
====================================================
Executes high-throughput causal-LM pretraining on Xeren's custom 214M Transformer
architecture using standard next-token cross-entropy over full token sequences.

Features:
- Full causal next-token prediction (no assistant-only masking)
- Microbatching with Gradient Accumulation
- Mixed-Precision FP16 AMP + PyTorch Gradient Checkpointing
- Cosine Learning Rate Schedule with Warmup
- Validation Loss & Perplexity Tracking
- Checkpointing & Resumption from Stage-1 Checkpoint
- Full GPU Telemetry (VRAM, step latency, throughput)
"""

import os
import sys
import json
import math
import time
import argparse
import random
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from training.src.model.xeren_transformer import XerenTransformer, XerenConfig
from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("xeren.foundation_trainer")


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class FoundationDataset(Dataset):
    """Causal LM Pretraining Dataset with Full Next-Token Targets."""

    def __init__(
        self,
        texts: List[str],
        tokenizer: XerenTokenizer,
        max_seq_len: int = 1024,
    ):
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.samples: List[Dict[str, torch.Tensor]] = []
        self._tokenize_all(texts)

    def _tokenize_all(self, texts: List[str]) -> None:
        pad_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
        eos_id = self.tokenizer.eos_token_id

        for text in texts:
            tokens = self.tokenizer.encode(text, add_special_tokens=True)
            if eos_id is not None and (not tokens or tokens[-1] != eos_id):
                tokens.append(eos_id)

            if len(tokens) > self.max_seq_len:
                tokens = tokens[:self.max_seq_len]

            seq_len = len(tokens)
            pad_len = self.max_seq_len - seq_len

            input_ids = tokens + [pad_id] * pad_len
            # Full sequence causal LM targets (loss computed on all real tokens, -100 on padding)
            labels = tokens + [-100] * pad_len
            attention_mask = [1] * seq_len + [0] * pad_len

            self.samples.append({
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "labels": torch.tensor(labels, dtype=torch.long),
                "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return self.samples[idx]


def get_cosine_schedule_with_warmup(
    optimizer: torch.optim.Optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
    min_lr_ratio: float = 0.1,
) -> torch.optim.lr_scheduler.LambdaLR:
    """Cosine learning rate decay with linear warmup."""
    def lr_lambda(current_step: int) -> float:
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def evaluate_foundation(
    model: XerenTransformer,
    val_loader: DataLoader,
    device: torch.device,
    use_amp: bool = True,
) -> Tuple[float, float]:
    """Compute validation loss and perplexity over validation dataset."""
    model.eval()
    total_loss = 0.0
    total_tokens = 0

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)

            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                out = model(input_ids, labels=labels)
                loss = out.get("loss")
                if loss is not None and not torch.isnan(loss):
                    valid_tokens = (labels != -100).sum().item()
                    total_loss += loss.item() * valid_tokens
                    total_tokens += valid_tokens

    model.train()
    avg_loss = total_loss / max(1, total_tokens)
    ppl = math.exp(min(avg_loss, 50.0))
    return avg_loss, ppl


def run_foundation_training(args: argparse.Namespace) -> None:
    """Main training loop."""
    set_seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.force_cpu else "cpu")
    logger.info(f"Target Hardware Device: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")

    # 1. Load Tokenizer
    tok_path = Path(args.tokenizer_path)
    logger.info(f"Loading Xeren 32K Tokenizer from: {tok_path}")
    tokenizer = XerenTokenizer.load(str(tok_path))

    # 2. Load Datasets
    logger.info(f"Loading train data from: {args.train_data}")
    with open(args.train_data, "r", encoding="utf-8") as f:
        train_texts = json.load(f)

    logger.info(f"Loading val data from: {args.val_data}")
    with open(args.val_data, "r", encoding="utf-8") as f:
        val_texts = json.load(f)

    train_dataset = FoundationDataset(train_texts, tokenizer, max_seq_len=args.max_seq_len)
    val_dataset = FoundationDataset(val_texts, tokenizer, max_seq_len=args.max_seq_len)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.micro_batch,
        shuffle=True,
        drop_last=True,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.micro_batch,
        shuffle=False,
        pin_memory=(device.type == "cuda"),
    )

    # 3. Model Initialization / Resumption
    logger.info(f"Loading Base Checkpoint: {args.base_checkpoint}")
    checkpoint = torch.load(args.base_checkpoint, map_location=device, weights_only=False)
    cfg_dict = checkpoint.get("config", {})

    if isinstance(cfg_dict, dict):
        model_kwargs = {
            "vocab_size": cfg_dict.get("vocab_size", 32768),
            "dim": cfg_dict.get("dim", cfg_dict.get("hidden_dim", 1024)),
            "n_layers": cfg_dict.get("n_layers", cfg_dict.get("num_layers", 16)),
            "n_heads": cfg_dict.get("n_heads", cfg_dict.get("num_heads", 16)),
            "n_kv_heads": cfg_dict.get("n_kv_heads", cfg_dict.get("num_kv_heads", 4)),
            "hidden_dim": cfg_dict.get("intermediate_dim", cfg_dict.get("hidden_dim_swiglu", 2816)),
            "max_seq_len": cfg_dict.get("max_seq_len", 2048),
            "tie_word_embeddings": cfg_dict.get("tie_word_embeddings", True),
        }
        config = XerenConfig(**model_kwargs)
    elif isinstance(cfg_dict, XerenConfig):
        config = cfg_dict
    else:
        config = XerenConfig(vocab_size=32768, dim=1024, n_layers=16, n_heads=16, n_kv_heads=4, hidden_dim=2816, max_seq_len=2048)

    model = XerenTransformer(config).to(device)
    if hasattr(model, "gradient_checkpointing"):
        model.gradient_checkpointing = True

    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    logger.info(f"Loaded {sum(p.numel() for p in model.parameters()):,} parameters successfully.")

    # 4. Optimization Setup
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        betas=(0.9, 0.95),
        eps=1e-8,
        weight_decay=0.01,
    )
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=args.warmup_steps,
        num_training_steps=args.max_steps,
    )
    scaler = torch.amp.GradScaler('cuda', enabled=(device.type == "cuda"))

    # Initial Validation
    init_val_loss, init_val_ppl = evaluate_foundation(model, val_loader, device)
    logger.info(f"Initial Baseline Validation Loss: {init_val_loss:.4f} | Perplexity: {init_val_ppl:.2f}")

    # 5. Training Loop
    model.train()
    step = 0
    total_tokens_processed = 0
    train_iter = iter(train_loader)
    t_start = time.time()
    accum_loss = 0.0

    logger.info("==========================================================================")
    logger.info("LAUNCHING XEREN FOUNDATION CONTINUOUS PRETRAINING")
    logger.info(f"Max Steps         : {args.max_steps:,}")
    logger.info(f"Effective Batch   : {args.micro_batch * args.grad_accum} (Micro: {args.micro_batch}, Accum: {args.grad_accum})")
    logger.info(f"Base Learning Rate: {args.lr}")
    logger.info("==========================================================================")

    while step < args.max_steps:
        optimizer.zero_grad(set_to_none=True)
        micro_loss_sum = 0.0

        for _ in range(args.grad_accum):
            try:
                batch = next(train_iter)
            except StopIteration:
                train_iter = iter(train_loader)
                batch = next(train_iter)

            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)
            valid_tokens = (labels != -100).sum().item()
            total_tokens_processed += valid_tokens

            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=(device.type == "cuda")):
                out = model(input_ids, labels=labels)
                loss = out["loss"] / args.grad_accum

            scaler.scale(loss).backward()
            micro_loss_sum += loss.item() * args.grad_accum

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip_grad)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        step += 1
        accum_loss = micro_loss_sum

        if step % args.log_interval == 0 or step == 1:
            curr_lr = scheduler.get_last_lr()[0]
            elapsed = time.time() - t_start
            vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if device.type == "cuda" else 0
            tps = total_tokens_processed / max(1e-5, elapsed)
            logger.info(
                f"Step {step:5d}/{args.max_steps} | Loss: {accum_loss:7.4f} | LR: {curr_lr:8.2e} | "
                f"VRAM: {vram_mb:6.1f} MB | Speed: {tps:6.1f} tok/s"
            )

        if step % args.eval_interval == 0:
            val_loss, val_ppl = evaluate_foundation(model, val_loader, device)
            logger.info(f"--- [EVAL Step {step}] Val Loss: {val_loss:.4f} | Val Perplexity: {val_ppl:.2f} ---")

        if step % args.save_interval == 0:
            output_dir.mkdir(parents=True, exist_ok=True)
            ckpt_p = output_dir / f"checkpoint_step_{step}.pt"
            torch.save({
                "step": step,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "config": config,
            }, ckpt_p)
            logger.info(f"Saved periodic checkpoint to: {ckpt_p}")

    # Final Evaluation & Save
    final_val_loss, final_val_ppl = evaluate_foundation(model, val_loader, device)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_ckpt = output_dir / "checkpoint_final.pt"
    torch.save({
        "step": step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": config,
        "val_loss": final_val_loss,
        "val_ppl": final_val_ppl,
    }, final_ckpt)
    logger.info(f"[DONE] Final Foundation Checkpoint Saved to: {final_ckpt}")
    logger.info(f"Final Val Loss: {final_val_loss:.4f} | Perplexity: {final_val_ppl:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Run Xeren Foundation Pretraining.")
    parser.add_argument("--base-checkpoint", type=str, default="training/checkpoints/stage1/checkpoint_final.pt")
    parser.add_argument("--train-data", type=str, default="training/data/processed/foundation_train.json")
    parser.add_argument("--val-data", type=str, default="training/data/processed/foundation_val.json")
    parser.add_argument("--output-dir", type=str, default="training/checkpoints/stage1_foundation")
    parser.add_argument("--tokenizer-path", type=str, default="training/checkpoints/tokenizer_32k")
    
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--micro-batch", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--clip-grad", type=float, default=1.0)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--log-interval", type=int, default=20)
    parser.add_argument("--eval-interval", type=int, default=200)
    parser.add_argument("--save-interval", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force-cpu", action="store_true")
    
    args = parser.parse_args()
    run_foundation_training(args)


if __name__ == "__main__":
    main()
