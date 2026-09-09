#!/usr/bin/env python3
"""
Xeren Foundation Pretraining Data Pipeline
==========================================
Acquires, filters, deduplicates, and structures high-volume Hugging Face datasets
for continuous causal-LM pretraining of the scratch-trained Xeren 214M Transformer.

Key Principles:
1. Foundation Pretraining != Alignment:
   - Uses full causal LM next-token prediction over entire token sequences.
   - Preserves raw Python code, mathematics, and encyclopedic text structures.
   - Conversational sources maintain native ChatML formatting.
2. Deduplication & Quality Filtering:
   - SHA-256 normalized hash filtering.
   - Alphanumeric density threshold (>0.65) to eliminate corrupted OCR/binary artifacts.
   - Character length bounds (50 to 8,000 characters).
3. Explicit Per-Source Allocation & Reporting.
4. Deterministic 95/5 Train/Validation Split (Seed 42).
"""

import os
import sys
import json
import hashlib
import re
import argparse
import random
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# Disable implicit expired HF token usage
os.environ.pop("HF_TOKEN", None)
os.environ.pop("HUGGING_FACE_HUB_TOKEN", None)
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("xeren.foundation_data")


class FoundationDataPipeline:
    """Manages multi-source dataset acquisition, preprocessing, tokenization, and splitting."""

    def __init__(
        self,
        tokenizer_path: Path,
        output_dir: Path,
        min_char_len: int = 50,
        max_char_len: int = 8000,
        val_ratio: float = 0.05,
        seed: int = 42,
    ):
        self.tokenizer_path = tokenizer_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.min_char_len = min_char_len
        self.max_char_len = max_char_len
        self.val_ratio = val_ratio
        self.seed = seed
        
        logger.info(f"Loading Xeren 32K Tokenizer from: {tokenizer_path}")
        self.tokenizer = XerenTokenizer.load(str(tokenizer_path))
        
        # State tracking
        self.seen_hashes: Set[str] = set()
        self.duplicate_count = 0
        self.rejected_count = 0
        self.source_stats: Dict[str, Dict[str, Any]] = {}

    def _compute_hash(self, text: str) -> str:
        """Normalized SHA-256 hash for exact/near-duplicate detection."""
        norm = re.sub(r"\s+", " ", text.lower().strip())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def _is_valid_text(self, text: str) -> bool:
        """Quality filter: length, alphanumeric density, and duplication."""
        if not text:
            self.rejected_count += 1
            return False
            
        t_len = len(text)
        if t_len < self.min_char_len or t_len > self.max_char_len:
            self.rejected_count += 1
            return False

        # Alphanumeric ratio
        alpha_count = sum(1 for c in text if c.isalnum() or c.isspace())
        if (alpha_count / max(t_len, 1)) < 0.65:
            self.rejected_count += 1
            return False

        # Deduplication
        text_hash = self._compute_hash(text)
        if text_hash in self.seen_hashes:
            self.duplicate_count += 1
            return False
            
        self.seen_hashes.add(text_hash)
        return True

    # -------------------------------------------------------------------------
    # Streamers with Source-Specific Formatting
    # -------------------------------------------------------------------------

    def stream_wikitext(self, target_samples: int) -> List[str]:
        """Raw encyclopedic knowledge & general English articles (Preserves raw document flow)."""
        logger.info(f"Streaming wikitext (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("wikitext", "wikitext-103-raw-v1", split="train", streaming=True, token=False)
            curr_doc = ""
            for item in ds:
                if len(samples) >= target_samples:
                    break
                line = item.get("text", "").strip()
                if not line:
                    if curr_doc and self._is_valid_text(curr_doc):
                        samples.append(curr_doc)
                    curr_doc = ""
                else:
                    curr_doc += line + "\n"
            if curr_doc and len(samples) < target_samples and self._is_valid_text(curr_doc):
                samples.append(curr_doc)
        except Exception as e:
            logger.warning(f"Failed to stream wikitext: {e}")
        return samples

    def stream_python_code(self, target_samples: int) -> List[str]:
        """Raw Python functions, docstrings, type annotations, and unit tests."""
        logger.info(f"Streaming iamtarun/python_code_instructions_18k_alpaca (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("iamtarun/python_code_instructions_18k_alpaca", split="train", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                inst = item.get("instruction", "").strip()
                inp = item.get("input", "").strip()
                out = item.get("output", "").strip()
                
                # Format as professional Python module with docstring
                if inp:
                    code_doc = f'"""\nTask: {inst}\nInput Specification: {inp}\n"""\n\n{out}'
                else:
                    code_doc = f'"""\nTask: {inst}\n"""\n\n{out}'
                    
                if self._is_valid_text(code_doc):
                    samples.append(code_doc)
        except Exception as e:
            logger.warning(f"Failed to stream python_code_instructions: {e}")
        return samples

    def stream_metamath(self, target_samples: int) -> List[str]:
        """Mathematical reasoning & step-by-step arithmetic proofs."""
        logger.info(f"Streaming meta-math/MetaMathQA (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("meta-math/MetaMathQA", split="train", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                query = item.get("query", "").strip()
                resp = item.get("response", "").strip()
                math_doc = f"# Problem:\n{query}\n\n# Step-by-Step Solution:\n{resp}"
                if self._is_valid_text(math_doc):
                    samples.append(math_doc)
        except Exception as e:
            logger.warning(f"Failed to stream MetaMathQA: {e}")
        return samples

    def stream_dolly(self, target_samples: int) -> List[str]:
        """Conversational instruction following & encyclopedic Q&A."""
        logger.info(f"Streaming databricks/databricks-dolly-15k (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("databricks/databricks-dolly-15k", split="train", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                inst = item.get("instruction", "").strip()
                ctx = item.get("context", "").strip()
                resp = item.get("response", "").strip()
                u_text = f"{inst}\n\nContext:\n{ctx}" if ctx else inst
                doc = (
                    f"<|im_start|>system\nYou are Xeren, an autonomous reasoning and action AI system.\n<|im_end|>\n"
                    f"<|im_start|>user\n{u_text}\n<|im_end|>\n"
                    f"<|im_start|>assistant\n{resp}\n<|im_end|>\n"
                )
                if self._is_valid_text(doc):
                    samples.append(doc)
        except Exception as e:
            logger.warning(f"Failed to stream Dolly-15k: {e}")
        return samples

    def stream_hotpotqa(self, target_samples: int) -> List[str]:
        """Multi-hop document retrieval & reasoning chains."""
        logger.info(f"Streaming hotpotqa/hotpot_qa (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split="train", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                q = item.get("question", "").strip()
                ans = item.get("answer", "").strip()
                ctx_list = item.get("context", {}).get("sentences", [])
                ctx_str = " ".join([" ".join(s) for s in ctx_list[:3]])[:1200]
                doc = f"## Background Reference Documents:\n{ctx_str}\n\n## Analysis Question:\n{q}\n\n## Verified Answer:\n{ans}"
                if self._is_valid_text(doc):
                    samples.append(doc)
        except Exception as e:
            logger.warning(f"Failed to stream HotpotQA: {e}")
        return samples

    def stream_xlam(self, target_samples: int) -> List[str]:
        """Tool definitions, JSON arguments, and structured schema dispatching."""
        logger.info(f"Streaming Salesforce/xlam-function-calling-60k (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("Salesforce/xlam-function-calling-60k", split="train", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                query = item.get("query", "").strip()
                tools = item.get("tools", "")
                answers = item.get("answers", "")
                doc = (
                    f"<|im_start|>system\nYou are Xeren, capable of structured JSON tool dispatch.\n<|im_end|>\n"
                    f"<|im_start|>user\nAvailable Tools:\n{tools}\n\nTask: {query}\n<|im_end|>\n"
                    f"<|im_start|>assistant\nAction: Dispatching Tool Call\n```json\n{answers}\n```\n<|im_end|>\n"
                )
                if self._is_valid_text(doc):
                    samples.append(doc)
        except Exception as e:
            logger.warning(f"Failed to stream xLAM-60k: {e}")
        return samples

    def stream_ultrachat(self, target_samples: int) -> List[str]:
        """Multi-turn dialogue and conversational reasoning."""
        logger.info(f"Streaming HuggingFaceH4/ultrachat_200k (target: {target_samples})...")
        samples = []
        try:
            from datasets import load_dataset
            ds = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft", streaming=True, token=False)
            for item in ds:
                if len(samples) >= target_samples:
                    break
                messages = item.get("messages", [])
                if len(messages) >= 2:
                    formatted = "<|im_start|>system\nYou are Xeren, an autonomous reasoning AI.\n<|im_end|>\n"
                    for m in messages[:4]:
                        r = m.get("role", "user")
                        c = m.get("content", "").strip()
                        formatted += f"<|im_start|>{r}\n{c}\n<|im_end|>\n"
                    if self._is_valid_text(formatted):
                        samples.append(formatted)
        except Exception as e:
            logger.warning(f"Failed to stream UltraChat-200k: {e}")
        return samples

    # -------------------------------------------------------------------------
    # Pipeline Orchestration & Token Analysis
    # -------------------------------------------------------------------------

    def run_pipeline(self, config: Dict[str, int]) -> Dict[str, Any]:
        """Executes acquisition, token counting, train/val split, and reporting."""
        random.seed(self.seed)
        all_samples: List[str] = []
        source_breakdown = {}

        source_methods = {
            "wikitext": (self.stream_wikitext, config.get("wikitext", 0)),
            "python_code": (self.stream_python_code, config.get("python_code", 0)),
            "metamath": (self.stream_metamath, config.get("metamath", 0)),
            "dolly_15k": (self.stream_dolly, config.get("dolly_15k", 0)),
            "hotpotqa": (self.stream_hotpotqa, config.get("hotpotqa", 0)),
            "xlam_tools": (self.stream_xlam, config.get("xlam_tools", 0)),
            "ultrachat": (self.stream_ultrachat, config.get("ultrachat", 0)),
        }

        for name, (method, target) in source_methods.items():
            if target > 0:
                logger.info(f"--- Processing source: {name} (Target: {target:,}) ---")
                data = method(target)
                all_samples.extend(data)
                
                # Compute source specific metrics
                s_chars = sum(len(x) for x in data)
                source_breakdown[name] = {
                    "samples": len(data),
                    "total_characters": s_chars,
                    "avg_chars_per_sample": round(s_chars / max(len(data), 1), 1)
                }

        random.shuffle(all_samples)
        total_samples = len(all_samples)
        logger.info(f"Total valid samples gathered: {total_samples:,}")

        # Token counting via Xeren 32K Tokenizer
        logger.info("Computing exact token counts with Xeren 32K Tokenizer...")
        total_tokens = 0
        total_chars = 0
        token_lengths: List[int] = []

        for sample in all_samples:
            total_chars += len(sample)
            enc = self.tokenizer.encode(sample, add_special_tokens=True)
            t_len = len(enc)
            token_lengths.append(t_len)
            total_tokens += t_len

        avg_tok = total_tokens / max(total_samples, 1)
        min_tok = min(token_lengths) if token_lengths else 0
        max_tok = max(token_lengths) if token_lengths else 0

        # Split 95% Train / 5% Val
        val_size = int(total_samples * self.val_ratio)
        train_samples = all_samples[val_size:]
        val_samples = all_samples[:val_size]

        train_tokens = sum(token_lengths[val_size:])
        val_tokens = sum(token_lengths[:val_size])

        # Write datasets
        train_path = self.output_dir / "foundation_train.json"
        val_path = self.output_dir / "foundation_val.json"
        report_path = self.output_dir / "foundation_data_report.json"

        with open(train_path, "w", encoding="utf-8") as f:
            json.dump(train_samples, f, indent=2)

        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(val_samples, f, indent=2)

        report = {
            "dataset_summary": {
                "total_samples": total_samples,
                "train_samples": len(train_samples),
                "val_samples": len(val_samples),
                "train_tokens": train_tokens,
                "val_tokens": val_tokens,
                "total_tokens": total_tokens,
                "total_characters": total_chars,
                "avg_tokens_per_sample": round(avg_tok, 2),
                "min_tokens_per_sample": min_tok,
                "max_tokens_per_sample": max_tok,
                "rejected_samples_count": self.rejected_count,
                "duplicate_samples_filtered": self.duplicate_count,
            },
            "source_breakdown": source_breakdown,
            "paths": {
                "train_data": str(train_path),
                "val_data": str(val_path),
            }
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info("==========================================================================")
        logger.info("XEREN FOUNDATION DATASET PREPARATION COMPLETE")
        logger.info(f"Total Samples    : {total_samples:,} (Train: {len(train_samples):,} | Val: {len(val_samples):,})")
        logger.info(f"Total Tokens     : {total_tokens:,} tokens (Avg: {avg_tok:.1f} tok/sample)")
        logger.info(f"Train Tokens     : {train_tokens:,} | Val Tokens: {val_tokens:,}")
        logger.info(f"Filtered Out     : {self.rejected_count} rejected | {self.duplicate_count} duplicates")
        logger.info(f"Artifacts Saved  : {train_path}, {val_path}, {report_path}")
        logger.info("==========================================================================")
        return report


def main():
    parser = argparse.ArgumentParser(description="Acquire & Process Xeren Foundation Pretraining Data.")
    parser.add_argument("--output-dir", type=str, default="training/data/processed", help="Output directory")
    parser.add_argument("--tokenizer-dir", type=str, default="training/checkpoints/tokenizer_32k", help="Tokenizer directory")
    
    # Explicit per-source allocation
    parser.add_argument("--wikitext-samples", type=int, default=5000, help="General English & encyclopedic articles")
    parser.add_argument("--python-samples", type=int, default=8000, help="Python code and functions")
    parser.add_argument("--metamath-samples", type=int, default=8000, help="Mathematics & arithmetic proofs")
    parser.add_argument("--dolly-samples", type=int, default=5000, help="Conversational instruction following")
    parser.add_argument("--hotpot-samples", type=int, default=5000, help="Multi-hop document reasoning")
    parser.add_argument("--xlam-samples", type=int, default=6000, help="Tool calling and JSON schemas")
    parser.add_argument("--ultrachat-samples", type=int, default=6000, help="Multi-turn dialogues")
    
    # Dry-run mode for quick testing
    parser.add_argument("--dry-run", action="store_true", help="Process 20 samples per source to verify pipeline")
    
    args = parser.parse_args()

    tok_path = REPO_ROOT / args.tokenizer_dir
    out_path = REPO_ROOT / args.output_dir

    if args.dry_run:
        config = {
            "wikitext": 20,
            "python_code": 20,
            "metamath": 20,
            "dolly_15k": 20,
            "hotpotqa": 20,
            "xlam_tools": 20,
            "ultrachat": 20,
        }
        logger.info("Running in DRY-RUN mode (20 samples per source)...")
    else:
        config = {
            "wikitext": args.wikitext_samples,
            "python_code": args.python_samples,
            "metamath": args.metamath_samples,
            "dolly_15k": args.dolly_samples,
            "hotpotqa": args.hotpot_samples,
            "xlam_tools": args.xlam_samples,
            "ultrachat": args.ultrachat_samples,
        }

    pipeline = FoundationDataPipeline(tokenizer_path=tok_path, output_dir=out_path)
    pipeline.run_pipeline(config)


if __name__ == "__main__":
    main()
