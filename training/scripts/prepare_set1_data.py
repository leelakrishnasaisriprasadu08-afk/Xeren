"""
Prepare Set 1 Datasets: Control Hub (Main Model Orchestrator + ToolCaller)
=========================================================================
Downloads and formats ONLY the targeted samples required for Set 1 models:
  1. Main Model Orchestrator:
     - Conversational fluency & instruction following (UltraChat subset, max 2000)
     - Sovereign Xeren identity & boundary compliance
     - High-level task decomposition trajectories
  2. ToolCaller:
     - Multi-specialist routing & dispatch JSON
     - Function calling trajectories with structured parameter validation

Storage & RAM Protection:
  - Strict sample caps: max 2,500 samples for Orchestrator, 1,500 for ToolCaller
  - Total disk footprint: < 15 MB of clean, ready-to-train JSONL
  - Automatic cache cleanup helper to wipe ~/.cache/huggingface/
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("xeren.set1_data_preparer")

SET1_DIR = REPO_ROOT / "training" / "data" / "set1_control_hub"
ORCH_DIR = SET1_DIR / "orchestrator"
TOOL_DIR = SET1_DIR / "tool_caller"

ORCH_DIR.mkdir(parents=True, exist_ok=True)
TOOL_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_hf_cache():
    """Purge temporary Hugging Face cache to keep disk space 100% clean."""
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        logger.info("Cleaning up temporary Hugging Face cache at %s...", hf_cache)
        try:
            shutil.rmtree(hf_cache, ignore_errors=True)
            logger.info("Cache successfully cleaned!")
        except Exception as e:
            logger.warning("Could not delete HF cache: %s", e)


def prepare_orchestrator_data(max_samples: int = 2500, force: bool = False):
    """Prepare high-quality, bounded dataset for the Main Model Orchestrator."""
    logger.info("--- Preparing Set 1: Main Model Orchestrator Data ---")
    train_file = ORCH_DIR / "train.jsonl"
    val_file   = ORCH_DIR / "val.jsonl"
    if train_file.exists() and not force:
        logger.info("Set 1 Orchestrator data already exists at %s (%.2f MB)", train_file, train_file.stat().st_size / 1e6)
        return

    samples = []

    # 1. Existing high-quality identity and orchestration data if available
    local_source = REPO_ROOT / "training" / "data" / "main_orchestrator" / "main_train.jsonl"
    if local_source.exists():
        logger.info("Loading base orchestrator data from %s...", local_source)
        with open(local_source, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        samples.append(json.loads(line))
                    except Exception:
                        continue
        logger.info("Loaded %d local orchestrator samples", len(samples))

    # 2. Stream a bounded subset of UltraChat (conversational flow)
    ultrachat_target = max(0, max_samples - len(samples))
    if ultrachat_target > 0:
        logger.info("Streaming %d conversational samples from UltraChat 200k...", ultrachat_target)
        try:
            from datasets import load_dataset
            ds = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft", streaming=True)
            count = 0
            for item in ds:
                msgs = item.get("messages", [])
                if len(msgs) >= 2:
                    formatted_msgs = [
                        {"role": "system", "content": "You are Xeren, an autonomous reasoning and action AI system capable of multi-step planning, tool execution, and precise coordination."},
                    ]
                    for m in msgs:
                        role = m.get("role", "user")
                        content = m.get("content", "")
                        formatted_msgs.append({"role": role, "content": content})
                    samples.append({"messages": formatted_msgs})
                    count += 1
                    if count >= ultrachat_target:
                        break
            logger.info("Successfully streamed %d UltraChat samples", count)
        except Exception as e:
            logger.warning("UltraChat streaming skipped or timed out (%s), continuing with local data", e)

    # Cap to max
    samples = samples[:max_samples]
    val_count = max(50, int(len(samples) * 0.05))
    train_samples = samples[val_count:]
    val_samples = samples[:val_count]

    train_file = ORCH_DIR / "train.jsonl"
    val_file = ORCH_DIR / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(s) + "\n")

    logger.info("Orchestrator dataset ready:")
    logger.info("  Train: %d samples (%.2f MB) -> %s", len(train_samples), train_file.stat().st_size / 1e6, train_file)
    logger.info("  Val:   %d samples (%.2f MB) -> %s", len(val_samples), val_file.stat().st_size / 1e6, val_file)


def prepare_tool_caller_data(max_samples: int = 1500, force: bool = False):
    """Prepare high-quality, bounded dataset for the ToolCaller model."""
    logger.info("--- Preparing Set 1: ToolCaller Neural Router Data ---")
    train_file = TOOL_DIR / "train.jsonl"
    val_file   = TOOL_DIR / "val.jsonl"
    if train_file.exists() and not force:
        logger.info("Set 1 ToolCaller data already exists at %s (%.2f MB)", train_file, train_file.stat().st_size / 1e6)
        return

    samples = []

    # 1. Existing high-quality multi-specialist routing trajectories if available
    local_source = REPO_ROOT / "training" / "data" / "tool_caller" / "tool_caller_train.jsonl"
    if local_source.exists():
        logger.info("Loading base tool caller data from %s...", local_source)
        with open(local_source, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        samples.append(json.loads(line))
                    except Exception:
                        continue
        logger.info("Loaded %d local tool caller samples", len(samples))

    samples = samples[:max_samples]
    val_count = max(50, int(len(samples) * 0.08))
    train_samples = samples[val_count:]
    val_samples = samples[:val_count]

    train_file = TOOL_DIR / "train.jsonl"
    val_file = TOOL_DIR / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(s) + "\n")

    logger.info("ToolCaller dataset ready:")
    logger.info("  Train: %d samples (%.2f MB) -> %s", len(train_samples), train_file.stat().st_size / 1e6, train_file)
    logger.info("  Val:   %d samples (%.2f MB) -> %s", len(val_samples), val_file.stat().st_size / 1e6, val_file)


def cleanup_intermediate_checkpoints():
    """Helper to remove epoch checkpoints, keeping only checkpoint_final.pt."""
    logger.info("--- Checking for intermediate checkpoints to clean ---")
    for ckpt_dir in [
        REPO_ROOT / "training" / "checkpoints" / "xeren_main_v2",
        REPO_ROOT / "training" / "checkpoints" / "mos" / "tool_caller",
    ]:
        if ckpt_dir.exists():
            final_ckpt = ckpt_dir / "checkpoint_final.pt"
            if final_ckpt.exists():
                for intermediate in ckpt_dir.glob("checkpoint_epoch*.pt"):
                    try:
                        sz = intermediate.stat().st_size / 1e6
                        intermediate.unlink()
                        logger.info("Deleted intermediate snapshot: %s (freed %.1f MB)", intermediate.name, sz)
                    except Exception as e:
                        logger.warning("Could not delete %s: %s", intermediate, e)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare Set 1 Training Data")
    parser.add_argument("--cleanup-only", action="store_true", help="Only run cleanup of HF cache and epoch snapshots")
    parser.add_argument("--no-hf-cleanup", action="store_true", help="Keep HF cache")
    args = parser.parse_args()

    if args.cleanup_only:
        cleanup_hf_cache()
        cleanup_intermediate_checkpoints()
    else:
        prepare_orchestrator_data()
        prepare_tool_caller_data()
        if not args.no_hf_cleanup:
            cleanup_hf_cache()
        cleanup_intermediate_checkpoints()
        logger.info("Set 1 data preparation and cleanup complete!")
