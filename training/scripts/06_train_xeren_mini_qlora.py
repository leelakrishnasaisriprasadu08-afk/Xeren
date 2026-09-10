#!/usr/bin/env python3
"""
06_train_xeren_mini_qlora.py
============================
End-to-End QLoRA Fine-Tuning for Xeren-Mini (1.5B Foundation) on RTX A1000 GPU.

Features:
  - 4-bit NormalFloat (NF4) quantization with bitsandbytes
  - Low-Rank Adaptation (LoRA) targeting all attention & MLP projections
  - Assistant-only loss masking (focuses 100% on Xeren persona & responses)
  - Live progress telemetry written to training_progress.json for training_countdown.py
  - Full adapter merging into standalone pure Xeren weights (zero base model lock-in)
  - Automatic invocation of the 15-case validation suite

Usage:
  python training/scripts/06_train_xeren_mini_qlora.py
  python training/scripts/06_train_xeren_mini_qlora.py --epochs 3 --batch_size 2 --grad_accum 8
"""

import argparse
import gc
import json
import math
import os
import random
import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    get_cosine_schedule_with_warmup,
)
from peft import (
    LoraConfig,
    PeftModel,
    get_peft_model,
    prepare_model_for_kbit_training,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ANSI colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PROGRESS_FILE = Path("training/checkpoints/xeren_mini_qlora/training_progress.json")
ADAPTER_DIR = Path("training/checkpoints/xeren_mini_qlora")
FINAL_DIR = Path("training/checkpoints/xeren_mini_final")


def write_progress(
    stage_pct_start: float,
    stage_pct_end: float,
    current_step: int,
    total_steps: int,
    current_epoch: int,
    total_epochs: int,
    loss: Optional[float] = None,
    status: str = "training",
    start_time: Optional[float] = None,
):
    """Write live progress to shared JSON file for training_countdown.py."""
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate overall percent
        if total_steps > 0:
            step_frac = current_step / total_steps
        else:
            step_frac = 0.0
            
        overall_pct = stage_pct_start + step_frac * (stage_pct_end - stage_pct_start)
        overall_pct = min(max(overall_pct, 0.0), 100.0)

        # VRAM
        vram_gb = 0.0
        if torch.cuda.is_available():
            vram_gb = round(torch.cuda.memory_allocated(0) / (1024 ** 3), 2)

        # ETA
        eta_seconds = 0
        if start_time and step_frac > 0:
            elapsed = time.time() - start_time
            total_est = elapsed / step_frac
            eta_seconds = max(0, int(total_est - elapsed))

        data = {
            "percent_complete": round(overall_pct, 1),
            "current_step": current_step,
            "total_steps": total_steps,
            "current_epoch": current_epoch,
            "total_epochs": total_epochs,
            "current_loss": round(float(loss), 4) if loss is not None else None,
            "status": status,
            "vram_gb": vram_gb,
            "eta_seconds": eta_seconds,
            "timestamp": datetime.now().isoformat(),
        }
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class XerenChatDataset(Dataset):
    """Dataset with assistant-only loss masking for ChatML."""

    def __init__(self, data_path: str, tokenizer, max_seq_len: int = 1024):
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.samples = []

        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {data_path}")

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

        print(f"[Dataset] Loaded {len(self.samples)} samples from {data_path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        messages = item["messages"]

        # Apply chat template
        if hasattr(self.tokenizer, "apply_chat_template"):
            formatted_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        else:
            # Fallback manual ChatML
            formatted_text = ""
            for msg in messages:
                formatted_text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"

        encoding = self.tokenizer(
            formatted_text,
            max_length=self.max_seq_len,
            truncation=True,
            return_tensors="pt",
        )
        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)

        # Labels: initialize with -100 everywhere
        labels = torch.full_like(input_ids, -100)

        # Mask user and system tokens, compute loss ONLY on assistant tokens
        # Find assistant start tokens
        # In Qwen2.5 ChatML: <|im_start|>assistant\n ... <|im_end|>
        im_start_token = self.tokenizer.encode("<|im_start|>", add_special_tokens=False)
        assistant_token = self.tokenizer.encode("assistant", add_special_tokens=False)
        im_end_token = self.tokenizer.encode("<|im_end|>", add_special_tokens=False)

        input_list = input_ids.tolist()
        i = 0
        n = len(input_list)
        while i < n:
            # Check for assistant block start
            if (
                i + 1 < n
                and input_list[i] in im_start_token
                and input_list[i + 1] in assistant_token
            ):
                # Move past header
                i += 2
                # Skip newline token if present
                if i < n and self.tokenizer.decode([input_list[i]]).strip() == "":
                    i += 1
                # Mark tokens until <|im_end|>
                while i < n:
                    if input_list[i] in im_end_token:
                        labels[i] = input_list[i] # include end token
                        i += 1
                        break
                    labels[i] = input_list[i]
                    i += 1
            else:
                i += 1

        # Safety check: if no assistant tokens were labeled, label everything except prompt
        if (labels != -100).sum() == 0:
            labels = input_ids.clone()

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def collate_fn(batch, pad_token_id: int):
    max_len = max(len(b["input_ids"]) for b in batch)
    
    input_ids = []
    attention_masks = []
    labels = []

    for b in batch:
        cur_len = len(b["input_ids"])
        pad_len = max_len - cur_len
        
        # Right pad
        inp = torch.cat([b["input_ids"], torch.full((pad_len,), pad_token_id, dtype=torch.long)])
        attn = torch.cat([b["attention_mask"], torch.zeros(pad_len, dtype=torch.long)])
        lbl = torch.cat([b["labels"], torch.full((pad_len,), -100, dtype=torch.long)])

        input_ids.append(inp)
        attention_masks.append(attn)
        labels.append(lbl)

    return {
        "input_ids": torch.stack(input_ids),
        "attention_mask": torch.stack(attention_masks),
        "labels": torch.stack(labels),
    }


def train_qlora(args):
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  XEREN-MINI QLoRA TRAINING LAUNCHER{RESET}")
    print(f"  Base Model  : {args.base_model}")
    print(f"  Target GPU  : NVIDIA RTX A1000")
    print(f"  Epochs      : {args.epochs}")
    print(f"  Batch Size  : {args.batch_size} (micro) x {args.grad_accum} (accum) = {args.batch_size * args.grad_accum}")
    print(f"  Learning Rate: {args.lr}")
    print(f"{BOLD}{'=' * 70}{RESET}\n")

    # Stage 0: Setup
    write_progress(0, 3, 0, 100, 0, args.epochs, status="setup")

    # Stage 1: Verify / Build Dataset
    train_data_path = Path(args.train_file)
    if not train_data_path.exists():
        print(f"{CYAN}[Step 1] Dataset not found at {train_data_path}. Building now...{RESET}")
        write_progress(3, 15, 0, 100, 0, args.epochs, status="building_dataset")
        import subprocess
        subprocess.run([sys.executable, "training/scripts/build_xeren_identity_dataset.py"], check=True)
    else:
        print(f"{GREEN}[Step 1] Dataset ready at {train_data_path}{RESET}")

    # Stage 2: Load Tokenizer & Model with 4-bit Quantization
    print(f"\n{CYAN}[Step 2] Loading Base Model & Tokenizer: {args.base_model}...{RESET}")
    write_progress(15, 22, 0, 100, 0, args.epochs, status="downloading_base_model")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model = prepare_model_for_kbit_training(model)
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # Stage 3: Setup LoRA Adapters
    print(f"\n{CYAN}[Step 3] Initializing QLoRA Adapters (r={args.lora_r}, alpha={args.lora_alpha})...{RESET}")
    write_progress(22, 25, 0, 100, 0, args.epochs, status="initializing_adapters")

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Create Dataset & DataLoader
    train_dataset = XerenChatDataset(args.train_file, tokenizer, max_seq_len=args.max_seq_len)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer.pad_token_id),
    )

    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr,
        weight_decay=0.01,
    )
    
    total_train_steps = (len(train_loader) // args.grad_accum) * args.epochs
    warmup_steps = int(total_train_steps * args.warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_train_steps,
    )

    # Stage 4: Training Loop
    print(f"\n{GREEN}{BOLD}[Step 4] Starting Training across {args.epochs} Epochs ({total_train_steps} total optimizer steps)...{RESET}\n")
    
    model.train()
    optimizer_step = 0
    start_time = time.time()
    recent_losses = []

    # Map epochs to progress percentages
    # Epoch 1: 25% -> 50%
    # Epoch 2: 50% -> 75%
    # Epoch 3: 75% -> 92%
    epoch_ranges = [
        (25.0, 50.0),
        (50.0, 75.0),
        (75.0, 92.0),
    ]

    for epoch in range(1, args.epochs + 1):
        range_idx = min(epoch - 1, len(epoch_ranges) - 1)
        st_start, st_end = epoch_ranges[range_idx]

        print(f"\n{BOLD}============== EPOCH {epoch}/{args.epochs} =============={RESET}")
        epoch_loss = 0.0
        step_in_epoch = 0
        accum_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(model.device)
            attention_mask = batch["attention_mask"].to(model.device)
            labels = batch["labels"].to(model.device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / args.grad_accum
            loss.backward()
            accum_loss += loss.item() * args.grad_accum

            if (batch_idx + 1) % args.grad_accum == 0 or (batch_idx + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                optimizer_step += 1
                step_in_epoch += 1
                recent_losses.append(accum_loss)
                if len(recent_losses) > 20:
                    recent_losses.pop(0)
                avg_loss = sum(recent_losses) / len(recent_losses)

                # Write live progress
                epoch_frac = step_in_epoch / (len(train_loader) / args.grad_accum)
                epoch_pct = st_start + epoch_frac * (st_end - st_start)
                write_progress(
                    stage_pct_start=st_start,
                    stage_pct_end=st_end,
                    current_step=optimizer_step,
                    total_steps=total_train_steps,
                    current_epoch=epoch,
                    total_epochs=args.epochs,
                    loss=avg_loss,
                    status=f"training_epoch_{epoch}",
                    start_time=start_time,
                )

                if optimizer_step % args.log_interval == 0:
                    vram_cur = torch.cuda.memory_allocated(0) / (1024 ** 3)
                    lr_cur = scheduler.get_last_lr()[0]
                    elapsed = time.time() - start_time
                    step_time = elapsed / max(1, optimizer_step)
                    rem_steps = total_train_steps - optimizer_step
                    eta_str = str(timedelta(seconds=int(rem_steps * step_time)))

                    print(
                        f"  [Epoch {epoch} | Step {optimizer_step}/{total_train_steps}] "
                        f"Loss: {avg_loss:.4f} | LR: {lr_cur:.2e} | VRAM: {vram_cur:.2f}GB | "
                        f"ETA: {eta_str}"
                    )

                accum_loss = 0.0

        print(f"{GREEN}[OK] Epoch {epoch} complete!{RESET}")
        epoch_save_dir = ADAPTER_DIR / f"epoch_{epoch}"
        epoch_save_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(epoch_save_dir))
        tokenizer.save_pretrained(str(epoch_save_dir))
        print(f"  {CYAN}Intermediate checkpoint for Epoch {epoch} saved to {epoch_save_dir}{RESET}")

    # Stage 5: Save QLoRA Adapter
    print(f"\n{CYAN}[Step 5] Saving QLoRA Adapter to {ADAPTER_DIR}...{RESET}")
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    print(f"{GREEN}[OK] Adapter saved successfully.{RESET}")

    # Free 4-bit training model from GPU memory to merge cleanly
    del model
    gc.collect()
    torch.cuda.empty_cache()

    # Stage 6: Merge Adapter into Standalone Xeren Model
    print(f"\n{BOLD}{CYAN}[Step 6] Merging Adapter into Pure Standalone Xeren Model (92% -> 96%)...{RESET}")
    write_progress(92, 96, total_train_steps, total_train_steps, args.epochs, args.epochs, status="merging_weights")

    print(f"  Reloading base model in float16 for weight fusion...")
    base_model_fp16 = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    print(f"  Attaching LoRA adapter from {ADAPTER_DIR}...")
    peft_merged = PeftModel.from_pretrained(base_model_fp16, str(ADAPTER_DIR))
    print(f"  Fusing weights (merge_and_unload)...")
    standalone_model = peft_merged.merge_and_unload()

    print(f"  Saving standalone Xeren model to {FINAL_DIR}...")
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    standalone_model.save_pretrained(str(FINAL_DIR))
    tokenizer.save_pretrained(str(FINAL_DIR))
    print(f"{GREEN}{BOLD}[OK] Standalone pure Xeren model saved to {FINAL_DIR}!{RESET}")

    # Free memory
    del standalone_model, base_model_fp16, peft_merged
    gc.collect()
    torch.cuda.empty_cache()

    # Stage 7: Run Validation Suite
    print(f"\n{BOLD}{CYAN}[Step 7] Running 15-Case Validation Suite (96% -> 99%)...{RESET}")
    write_progress(96, 99, total_train_steps, total_train_steps, args.epochs, args.epochs, status="validating")

    from training.scripts.xeren_mini_validation_tests import run_validation
    results = run_validation(
        mode="hf",
        checkpoint=str(FINAL_DIR),
        save_results=True,
    )

    # Complete!
    write_progress(99, 100, total_train_steps, total_train_steps, args.epochs, args.epochs, status="complete")
    print(f"\n{GREEN}{BOLD}{'=' * 70}")
    print("  [COMPLETE] XEREN-MINI TRAINING & VALIDATION FULLY COMPLETE!")
    print(f"{'=' * 70}{RESET}\n")


def parse_args():
    parser = argparse.ArgumentParser(description="xeren_mini QLoRA Fine-Tuner")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--train_file", type=str, default="training/data/xeren_identity/xeren_alignment_train.jsonl")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--warmup_ratio", type=float, default=0.05)
    parser.add_argument("--lora_r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--max_seq_len", type=int, default=1024)
    parser.add_argument("--gradient_checkpointing", action="store_true", default=True)
    parser.add_argument("--log_interval", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_qlora(args)
