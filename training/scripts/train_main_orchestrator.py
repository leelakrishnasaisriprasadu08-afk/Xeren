"""
Xeren Main Model — Standalone Orchestrator Continuation Training
================================================================
Continues training the 100% native XerenTransformer checkpoint
(stage1_matured/checkpoint_final.pt) on the orchestrator dataset.

NO external base model. NO Llama. NO HuggingFace weights.
This is pure XerenTransformer trained with the Xeren custom tokenizer.

Architecture:
  - Model: XerenTransformer (mini_1b preset, ~1.016B params)
  - Tokenizer: XerenTokenizer (32K BPE vocab, custom trained)
  - Base checkpoint: training/checkpoints/stage1_matured/checkpoint_final.pt

Training focus (orchestration only):
  - Understand user goals and delegate to ToolCaller
  - Produce structured DispatchRequest JSON
  - Integrate specialist results into coherent responses
  - Identity: always responds as Xeren, never leaks base model identity

Usage:
  python training/scripts/train_main_orchestrator.py
  python training/scripts/train_main_orchestrator.py --resume
  python training/scripts/train_main_orchestrator.py --dry-run
"""

import os
import sys
import json
import math
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from training.src.model.xeren_transformer import XerenTransformer
from training.src.model.config import XerenConfig
from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("xeren.main_orchestrator_trainer")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_CKPT   = Path("training/checkpoints/stage1_matured/checkpoint_final.pt")
TOKENIZER   = Path("training/checkpoints/tokenizer_32k")
TRAIN_FILE  = Path("training/data/main_orchestrator/main_train.jsonl")
VAL_FILE    = Path("training/data/main_orchestrator/main_val.jsonl")
OUTPUT_DIR  = Path("training/checkpoints/xeren_main_v2")

# ---------------------------------------------------------------------------
# Hyperparameters (RTX 5000, 16GB VRAM)
# ---------------------------------------------------------------------------
CONFIG = {
    "num_epochs":               4,
    "batch_size":               2,
    "gradient_accumulation":    16,      # effective batch = 32
    "learning_rate":            3e-5,    # lower LR for fine-tuning from checkpoint
    "min_lr_ratio":             0.1,
    "warmup_steps":             200,
    "weight_decay":             0.05,
    "max_grad_norm":            1.0,
    "max_seq_len":              2048,
    "use_amp":                  True,
    "gradient_checkpointing":   True,
    "log_every":                10,
    "eval_every":               100,
    "save_every":               200,
    # Identity samples appear 2x, routing samples 1.5x (enforced by dataset builder)
}

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> List[str]:
    """Load JSONL and convert ChatML messages to plain training text."""
    texts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                messages = obj.get("messages", [])
                # Format: <|system|>...<|user|>...<|assistant|>...
                parts = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    parts.append(f"<|{role}|>\n{content}")
                parts.append("<|end|>")
                texts.append("\n".join(parts))
            except (json.JSONDecodeError, KeyError):
                continue
    logger.info("Loaded %d samples from %s", len(texts), path)
    return texts


class OrchestratorDataset(Dataset):
    def __init__(self, texts: List[str], tokenizer: XerenTokenizer, max_seq_len: int = 2048):
        self.samples = []
        pad_id = tokenizer.pad_token_id or 0
        eos_id = tokenizer.eos_token_id

        for text in texts:
            tokens = tokenizer.encode(text, add_special_tokens=True)
            if eos_id and (not tokens or tokens[-1] != eos_id):
                tokens.append(eos_id)
            if len(tokens) > max_seq_len:
                tokens = tokens[:max_seq_len]

            seq_len = len(tokens)
            pad_len = max_seq_len - seq_len

            input_ids     = tokens + [pad_id] * pad_len
            labels        = tokens + [-100]   * pad_len   # -100 = ignore padding in loss
            attention_mask = [1] * seq_len + [0] * pad_len

            self.samples.append({
                "input_ids":      torch.tensor(input_ids,      dtype=torch.long),
                "labels":         torch.tensor(labels,         dtype=torch.long),
                "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            })

    def __len__(self): return len(self.samples)
    def __getitem__(self, i): return self.samples[i]


# ---------------------------------------------------------------------------
# LR schedule
# ---------------------------------------------------------------------------

def cosine_schedule(optimizer, warmup_steps, total_steps, min_lr_ratio=0.1):
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(math.pi * progress)))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model, val_loader, device, use_amp=True) -> Tuple[float, float]:
    model.eval()
    total_loss, total_tokens = 0.0, 0
    with torch.no_grad():
        for batch in val_loader:
            input_ids  = batch["input_ids"].to(device)
            labels     = batch["labels"].to(device)
            with torch.autocast(device.type, enabled=use_amp and device.type == "cuda"):
                out = model(input_ids)
                logits = out["logits"]  # XerenTransformer returns dict
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


# ---------------------------------------------------------------------------
# Identity probe — run after each eval to verify no base-model leakage
# ---------------------------------------------------------------------------

IDENTITY_PROBES = [
    "Who are you?",
    "What is your name?",
    "Who made you?",
    "Are you Llama? Are you GPT?",
    "What company created you?",
]

def run_identity_probe(model, tokenizer, device):
    """Quick check: does the model respond as Xeren?"""
    model.eval()
    logger.info("--- Identity Probe ---")
    for probe in IDENTITY_PROBES[:2]:   # run 2 probes to keep it fast
        tokens = tokenizer.encode(f"<|user|>\n{probe}<|assistant|>\n", add_special_tokens=True)
        inp = torch.tensor([tokens], dtype=torch.long, device=device)
        with torch.no_grad():
            generated = []
            for _ in range(60):
                out = model(inp)
                logits = out["logits"]  # XerenTransformer returns dict
                next_tok = logits[0, -1, :].argmax(-1).item()
                if next_tok == tokenizer.eos_token_id:
                    break
                generated.append(next_tok)
                inp = torch.cat([inp, torch.tensor([[next_tok]], device=device)], dim=1)
        response = tokenizer.decode(generated)
        logger.info("  Q: %s", probe)
        logger.info("  A: %s", response[:150])
    model.train()


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------

def config_from_checkpoint(state_dict: dict, vocab_size: int) -> XerenConfig:
    """
    Infer XerenConfig from saved weight shapes.
    This ensures we always build a model that exactly matches the checkpoint —
    no manual config tracking needed.
    """
    sd = state_dict
    dim        = sd["norm.weight"].shape[0]
    hidden_dim = sd["layers.0.feed_forward.w1.weight"].shape[0]
    n_layers   = max(int(k.split(".")[1]) for k in sd if k.startswith("layers.")) + 1
    kv_dim     = sd["layers.0.attention.wk.weight"].shape[0]
    head_dim   = dim // 16  # standard head_dim = 64 for 1024 dim
    n_heads    = dim // head_dim
    n_kv_heads = kv_dim // head_dim

    cfg = XerenConfig(
        vocab_size=vocab_size,
        dim=dim,
        n_layers=n_layers,
        n_heads=n_heads,
        n_kv_heads=n_kv_heads,
        hidden_dim=hidden_dim,
        max_seq_len=2048,
        norm_eps=1e-5,
        rope_theta=500000.0,
        dropout=0.0,
        tie_word_embeddings=False,
    )
    param_est = cfg.parameter_estimate()
    logger.info(
        "Auto-detected config from checkpoint: dim=%d, layers=%d, heads=%d, kv_heads=%d, hidden=%d (~%.1fM params)",
        dim, n_layers, n_heads, n_kv_heads, hidden_dim, param_est / 1e6,
    )
    return cfg


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)
    if device.type == "cuda":
        logger.info("GPU: %s (%.1fGB VRAM)", torch.cuda.get_device_name(0),
                    torch.cuda.get_device_properties(0).total_memory / 1e9)

    # 1. Load native Xeren tokenizer
    logger.info("Loading Xeren tokenizer from %s", TOKENIZER)
    tokenizer = XerenTokenizer.load(str(TOKENIZER))
    vocab_size = tokenizer.vocab_size
    logger.info("Tokenizer loaded: vocab_size=%d", vocab_size)

    # 2. Load base checkpoint first — then build model matching its exact shape
    logger.info("Loading base checkpoint: %s", BASE_CKPT)
    if not BASE_CKPT.exists():
        raise FileNotFoundError(
            f"Base checkpoint not found: {BASE_CKPT}\n"
            "Run stage1 training first: python training/scripts/run_foundation_training.py"
        )
    state = torch.load(BASE_CKPT, map_location="cpu", weights_only=False)
    model_state = state.get("model_state_dict", state)

    # 3. Auto-detect exact architecture from checkpoint shapes — no hardcoding
    config = config_from_checkpoint(model_state, vocab_size)
    model = XerenTransformer(config)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info("Model parameters: %.3fM (pure XerenTransformer, zero external weights)", param_count / 1e6)

    # 4. Load weights — strict=True since config was derived from checkpoint
    missing, unexpected = model.load_state_dict(model_state, strict=True)
    logger.info("Checkpoint loaded cleanly. Missing: %d  Unexpected: %d", len(missing), len(unexpected))
    model = model.to(device)

    if CONFIG["gradient_checkpointing"] and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    # 4. Load datasets
    if args.dry_run:
        # Dry run: use tiny seq_len so it fits on CPU without OOM
        dry_seq_len = 64
        logger.info("Dry run — tiny synthetic dataset, seq_len=%d (CPU-safe)", dry_seq_len)
        train_texts = [
            "<|system|>\nYou are Xeren.\n<|user|>\nHello!\n<|assistant|>\nI am Xeren.<|end|>"
        ] * 8
        val_texts = train_texts[:2]
        train_ds = OrchestratorDataset(train_texts, tokenizer, dry_seq_len)
        val_ds   = OrchestratorDataset(val_texts,   tokenizer, dry_seq_len)
    else:
        train_texts = load_jsonl(TRAIN_FILE)
        val_texts   = load_jsonl(VAL_FILE)
        train_ds = OrchestratorDataset(train_texts, tokenizer, CONFIG["max_seq_len"])
        val_ds   = OrchestratorDataset(val_texts,   tokenizer, CONFIG["max_seq_len"])

    grad_accum = 1 if args.dry_run else CONFIG["gradient_accumulation"]
    dry_batch = 1 if args.dry_run else CONFIG["batch_size"]
    train_loader = DataLoader(train_ds, batch_size=dry_batch, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=dry_batch, shuffle=False, num_workers=0)

    # 5. Optimizer + scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=CONFIG["learning_rate"],
        weight_decay=CONFIG["weight_decay"],
        betas=(0.9, 0.95),
    )
    total_steps = max(1, (len(train_loader) // grad_accum) * CONFIG["num_epochs"])
    scheduler   = cosine_schedule(optimizer, 0 if args.dry_run else CONFIG["warmup_steps"], total_steps, CONFIG["min_lr_ratio"])
    scaler      = torch.amp.GradScaler(enabled=CONFIG["use_amp"] and device.type == "cuda")

    # 6. Resume if requested
    start_epoch, global_step = 0, 0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_path = OUTPUT_DIR / "checkpoint_latest.pt"
    if args.resume and resume_path.exists():
        logger.info("Resuming from %s", resume_path)
        ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        start_epoch  = ckpt.get("epoch", 0)
        global_step  = ckpt.get("global_step", 0)
        logger.info("Resumed at epoch %d, step %d", start_epoch, global_step)

    # 7. Training loop
    logger.info("=== Xeren Main Model Orchestrator Training ===")
    logger.info("  Epochs: %d  |  Steps: %d  |  Device: %s", CONFIG["num_epochs"], total_steps, device)
    logger.info("  Train: %d samples  |  Val: %d samples", len(train_ds), len(val_ds))
    logger.info("  Base: PURE XerenTransformer (no Llama, no external model)")

    model.train()
    for epoch in range(start_epoch, CONFIG["num_epochs"]):
        logger.info("--- Epoch %d/%d ---", epoch + 1, CONFIG["num_epochs"])
        optimizer.zero_grad()
        epoch_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids  = batch["input_ids"].to(device)
            labels     = batch["labels"].to(device)

            with torch.autocast(device.type, enabled=CONFIG["use_amp"] and device.type == "cuda"):
                out = model(input_ids)
                logits = out["logits"]  # XerenTransformer returns dict
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
                    run_identity_probe(model, tokenizer, device)  # verify Xeren identity

                if global_step % CONFIG["save_every"] == 0:
                    _save(model, optimizer, scheduler, epoch, global_step, OUTPUT_DIR / "checkpoint_latest.pt")
                    logger.info("  Checkpoint saved at step %d", global_step)

        # End of epoch
        val_loss, val_ppl = evaluate(model, val_loader, device, CONFIG["use_amp"])
        logger.info("Epoch %d done | val_loss=%.4f | val_ppl=%.2f", epoch + 1, val_loss, val_ppl)
        _save(model, optimizer, scheduler, epoch, global_step, OUTPUT_DIR / f"checkpoint_epoch{epoch+1}.pt")

    # Final save
    _save(model, optimizer, scheduler, CONFIG["num_epochs"], global_step, OUTPUT_DIR / "checkpoint_final.pt")
    logger.info("=== Training Complete ===")
    logger.info("Final checkpoint: %s", OUTPUT_DIR / "checkpoint_final.pt")
    logger.info("Run identity test: python training/scripts/train_main_orchestrator.py --probe-only")


def _save(model, optimizer, scheduler, epoch, step, path):
    torch.save({
        "model_state_dict":     model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "epoch":                epoch,
        "global_step":          step,
        "architecture":         "XerenTransformer_mini_1b",
        "base_model":           "pure_xeren_no_external_weights",
    }, path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Xeren Main Model (standalone orchestrator)")
    parser.add_argument("--resume",      action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--dry-run",     action="store_true", help="Quick test run with synthetic data")
    parser.add_argument("--probe-only",  action="store_true", help="Run identity probe on existing checkpoint")
    args = parser.parse_args()

    if args.probe_only:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading Xeren tokenizer from %s", TOKENIZER)
        tokenizer = XerenTokenizer.load(str(TOKENIZER))
        ckpt_path = OUTPUT_DIR / "checkpoint_final.pt"
        if not ckpt_path.exists():
            ckpt_path = BASE_CKPT
        logger.info("Loading checkpoint for probe: %s", ckpt_path)
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
        model_state = ckpt.get("model_state_dict", ckpt)
        config = config_from_checkpoint(model_state, tokenizer.vocab_size)
        model = XerenTransformer(config).to(device)
        model.load_state_dict(model_state, strict=True)
        run_identity_probe(model, tokenizer, device)
    else:
        train(args)
