"""
Xeren MoS — ToolCaller Neural Routing Model Training
====================================================
Trains the specialized ToolCaller model on tool routing and dispatch JSON.
Builds directly on pure native XerenTransformer weights (stage1_matured checkpoint).

Features:
- Pure XerenTransformer + native 32K XerenTokenizer
- Saves to: training/checkpoints/mos/tool_caller/checkpoint_final.pt
- Automatic model architecture inference via checkpoint_utils
- Full support for --dry-run, --resume, and --probe-only
"""

import os
import sys
import json
import math
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from training.src.model.xeren_transformer import XerenTransformer
from training.src.model.checkpoint_utils import (
    config_from_checkpoint,
    load_native_xeren_model,
    generate_text,
)
from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("xeren.tool_caller_trainer")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_CKPT  = Path("training/checkpoints/stage1_matured/checkpoint_final.pt")
TOKENIZER  = Path("training/checkpoints/tokenizer_32k")
TRAIN_FILE = Path("training/data/set1_control_hub/tool_caller/train.jsonl")
VAL_FILE   = Path("training/data/set1_control_hub/tool_caller/val.jsonl")
OUTPUT_DIR = Path("training/checkpoints/mos/tool_caller")


# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
CONFIG = {
    "num_epochs":             4,
    "batch_size":             2,
    "gradient_accumulation":  8,
    "learning_rate":          5e-5,
    "min_lr_ratio":           0.1,
    "warmup_steps":           50,
    "weight_decay":           0.05,
    "max_grad_norm":          1.0,
    "max_seq_len":            1024,
    "use_amp":                True,
    "gradient_checkpointing": True,
    "log_every":              10,
    "eval_every":             50,
    "save_every":             100,
}


def load_jsonl(path: Path) -> List[str]:
    """Load JSONL dataset formatting messages to text."""
    texts = []
    if not path.exists():
        logger.warning("Dataset not found: %s", path)
        return texts

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                messages = obj.get("messages", [])
                parts = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    parts.append(f"<|{role}|>\n{content}")
                parts.append("<|end|>")
                texts.append("\n".join(parts))
            except Exception:
                continue
    logger.info("Loaded %d samples from %s", len(texts), path)
    return texts


class ToolCallerDataset(Dataset):
    def __init__(self, texts: List[str], tokenizer: XerenTokenizer, max_seq_len: int = 1024):
        self.samples = []
        pad_id = tokenizer.pad_token_id or 0
        eos_id = tokenizer.eos_token_id

        for text in texts:
            tokens = tokenizer.encode(text, add_special_tokens=False)
            if eos_id is not None and (not tokens or tokens[-1] != eos_id):
                tokens.append(eos_id)

            if len(tokens) > max_seq_len:
                tokens = tokens[:max_seq_len]

            input_ids = tokens[:-1]
            labels    = tokens[1:]

            pad_len = (max_seq_len - 1) - len(input_ids)
            if pad_len > 0:
                input_ids = input_ids + [pad_id] * pad_len
                labels    = labels    + [-100]   * pad_len

            self.samples.append({
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "labels":    torch.tensor(labels,    dtype=torch.long),
            })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def cosine_schedule(optimizer, warmup_steps, total_steps, min_lr_ratio=0.1):
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(math.pi * progress)))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def evaluate(model, val_loader, device, use_amp=True) -> Tuple[float, float]:
    model.eval()
    total_loss, total_tokens = 0.0, 0
    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            labels    = batch["labels"].to(device)
            with torch.autocast(device.type, enabled=use_amp and device.type == "cuda"):
                out = model(input_ids)
                logits = out["logits"]
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = labels[:, 1:].contiguous()
                loss = nn.functional.cross_entropy(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                    ignore_index=-100,
                    reduction="sum",
                )
            mask = (shift_labels != -100)
            total_loss   += loss.item()
            total_tokens += mask.sum().item()
    model.train()
    avg_loss   = total_loss / max(total_tokens, 1)
    perplexity = math.exp(min(avg_loss, 20))
    return avg_loss, perplexity


def run_routing_probe(model, tokenizer, device):
    """Test routing accuracy on sample dispatch queries."""
    model.eval()
    logger.info("--- ToolCaller Routing Probe ---")
    test_queries = [
        "Implement quicksort in Python with benchmark tests",
        "Explain quantum entanglement and verify the mathematical formulation",
    ]
    for q in test_queries:
        prompt = (
            f"<|system|>\nYou are Xeren ToolCaller.\n"
            f"<|user|>\n{q}\n"
            f"<|assistant|>\n"
        )
        ans = generate_text(model, tokenizer, prompt, max_new_tokens=80, temperature=0.2, device=device)
        logger.info("  Query: %s", q)
        logger.info("  Dispatch: %s", ans[:160])


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)
    if device.type == "cuda":
        logger.info("GPU: %s (%.1fGB VRAM)", torch.cuda.get_device_name(0),
                    torch.cuda.get_device_properties(0).total_memory / 1e9)

    logger.info("Loading Xeren tokenizer from %s", TOKENIZER)
    tokenizer = XerenTokenizer.load(str(TOKENIZER))
    vocab_size = tokenizer.vocab_size

    logger.info("Loading base checkpoint: %s", BASE_CKPT)
    if not BASE_CKPT.exists():
        raise FileNotFoundError(f"Base checkpoint not found at: {BASE_CKPT}")

    state = torch.load(BASE_CKPT, map_location="cpu", weights_only=False)
    model_state = state.get("model_state_dict", state)

    config = config_from_checkpoint(model_state, vocab_size)
    model = XerenTransformer(config)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info("Model parameters: %.3fM (pure XerenTransformer)", param_count / 1e6)

    missing, unexpected = model.load_state_dict(model_state, strict=True)
    logger.info("Checkpoint loaded cleanly. Missing: %d  Unexpected: %d", len(missing), len(unexpected))
    model = model.to(device)

    if CONFIG["gradient_checkpointing"] and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    if args.dry_run:
        dry_seq_len = 64
        logger.info("Dry run mode — using synthetic sample, seq_len=%d", dry_seq_len)
        train_texts = [
            "<|system|>\nYou are Xeren ToolCaller.\n<|user|>\nSort array.\n<|assistant|>\n{\"specialist\": \"M7_coding\"}<|end|>"
        ] * 8
        val_texts = train_texts[:2]
        train_ds = ToolCallerDataset(train_texts, tokenizer, dry_seq_len)
        val_ds   = ToolCallerDataset(val_texts,   tokenizer, dry_seq_len)
    else:
        train_path = Path(args.train_file) if args.train_file else TRAIN_FILE
        val_path   = Path(args.val_file)   if args.val_file   else VAL_FILE
        train_texts = load_jsonl(train_path)
        val_texts   = load_jsonl(val_path)
        train_ds = ToolCallerDataset(train_texts, tokenizer, CONFIG["max_seq_len"])
        val_ds   = ToolCallerDataset(val_texts,   tokenizer, CONFIG["max_seq_len"])

    grad_accum = 1 if args.dry_run else CONFIG["gradient_accumulation"]
    dry_batch = 1 if args.dry_run else CONFIG["batch_size"]
    train_loader = DataLoader(train_ds, batch_size=dry_batch, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=dry_batch, shuffle=False, num_workers=0)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=CONFIG["learning_rate"],
        weight_decay=CONFIG["weight_decay"],
        betas=(0.9, 0.95),
    )
    num_epochs = args.epochs if args.epochs else CONFIG["num_epochs"]
    total_steps = max(1, (len(train_loader) // grad_accum) * num_epochs)
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    scheduler   = cosine_schedule(optimizer, 0 if args.dry_run else CONFIG["warmup_steps"], total_steps, CONFIG["min_lr_ratio"])
    scaler      = torch.amp.GradScaler(enabled=CONFIG["use_amp"] and device.type == "cuda")

    start_epoch, global_step = 0, 0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_path = OUTPUT_DIR / "checkpoint_latest.pt"
    if args.resume and resume_path.exists():
        logger.info("Resuming from %s", resume_path)
        ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        start_epoch = ckpt.get("epoch", 0)
        global_step = ckpt.get("global_step", 0)

    logger.info("=== Xeren ToolCaller Training Started ===")
    logger.info("  Epochs: %d  |  Total Target Steps: %d  |  Device: %s", num_epochs, total_steps, device)
    logger.info("  Train: %d samples  |  Val: %d samples", len(train_ds), len(val_ds))

    model.train()
    stop_training = False
    for epoch in range(start_epoch, num_epochs):
        if stop_training:
            break
        logger.info("--- Epoch %d/%d ---", epoch + 1, num_epochs)
        optimizer.zero_grad()
        epoch_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            labels    = batch["labels"].to(device)

            with torch.autocast(device.type, enabled=CONFIG["use_amp"] and device.type == "cuda"):
                out = model(input_ids)
                logits = out["logits"]
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = labels[:, 1:].contiguous()
                loss = nn.functional.cross_entropy(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                    ignore_index=-100,
                )
                loss = loss / grad_accum

            scaler.scale(loss).backward()
            epoch_loss += loss.item() * grad_accum

            if (step + 1) % grad_accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), CONFIG["max_grad_norm"])
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                scheduler.step()
                global_step += 1

                if global_step % CONFIG["log_every"] == 0:
                    lr = scheduler.get_last_lr()[0]
                    logger.info("  step=%d  loss=%.4f  lr=%.2e", global_step, epoch_loss / max(step, 1), lr)

                if global_step % CONFIG["eval_every"] == 0:
                    val_loss, val_ppl = evaluate(model, val_loader, device, CONFIG["use_amp"])
                    logger.info("  [EVAL] val_loss=%.4f  val_ppl=%.2f", val_loss, val_ppl)

                if global_step % CONFIG["save_every"] == 0:
                    _save(model, optimizer, scheduler, epoch, global_step, OUTPUT_DIR / "checkpoint_latest.pt")

                if args.max_steps and global_step >= args.max_steps:
                    logger.info("Reached maximum steps limit (%d). Concluding training loop.", args.max_steps)
                    stop_training = True
                    break

        val_loss, val_ppl = evaluate(model, val_loader, device, CONFIG["use_amp"])
        logger.info("Epoch %d done | val_loss=%.4f | val_ppl=%.2f", epoch + 1, val_loss, val_ppl)
        if args.keep_epochs:
            _save(model, optimizer, scheduler, epoch, global_step, OUTPUT_DIR / f"checkpoint_epoch{epoch+1}.pt")

    _save(model, optimizer, scheduler, num_epochs, global_step, OUTPUT_DIR / "checkpoint_final.pt")
    logger.info("=== ToolCaller Training Complete ===")
    logger.info("Final checkpoint: %s", OUTPUT_DIR / "checkpoint_final.pt")

    # Clean intermediate snapshots to conserve disk space
    if not args.keep_epochs:
        logger.info("Preserving disk space: cleaning intermediate epoch snapshots...")
        for old_epoch in OUTPUT_DIR.glob("checkpoint_epoch*.pt"):
            try:
                old_epoch.unlink()
                logger.info("Removed: %s", old_epoch.name)
            except Exception:
                pass


def _save(model, optimizer, scheduler, epoch, step, path):
    torch.save({
        "model_state_dict":     model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "epoch":                epoch,
        "global_step":          step,
        "architecture":         "XerenTransformer_ToolCaller",
        "base_model":           "pure_xeren_native",
    }, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Xeren ToolCaller Routing Model")
    parser.add_argument("--resume",       action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--dry-run",      action="store_true", help="Quick test run with synthetic data")
    parser.add_argument("--probe-only",   action="store_true", help="Run routing probe on checkpoint")
    parser.add_argument("--train-file",   type=str, default=None, help="Path to train jsonl")
    parser.add_argument("--val-file",     type=str, default=None, help="Path to val jsonl")
    parser.add_argument("--epochs",       type=int, default=None, help="Number of epochs to train")
    parser.add_argument("--max-steps",    type=int, default=None, help="Max steps limit")
    parser.add_argument("--keep-epochs",  action="store_true", help="Keep epoch checkpoints (uses multi-GB disk)")
    args = parser.parse_args()

    if args.probe_only:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = XerenTokenizer.load(str(TOKENIZER))
        ckpt_path = OUTPUT_DIR / "checkpoint_final.pt"
        if not ckpt_path.exists():
            ckpt_path = BASE_CKPT
        logger.info("Loading checkpoint for probe: %s", ckpt_path)
        model, cfg = load_native_xeren_model(ckpt_path, tokenizer.vocab_size, device=device)
        run_routing_probe(model, tokenizer, device)
    else:
        train(args)
