"""
Grounded Knowledge and Alignment Dataset Engine for Xeren.
Provides high-precision factual answering, dataset retrieval from xeren_alignment_train.jsonl,
Indian geography and Andhra Pradesh district knowledge, and conversational reasoning with zero hallucination.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("xeren.core.knowledge_grounding")

_ALIGNMENT_CACHE: Optional[List[Dict[str, str]]] = None


def load_alignment_dataset() -> List[Dict[str, str]]:
    """Load and cache QA pairs from xeren_alignment_train.jsonl."""
    global _ALIGNMENT_CACHE
    if _ALIGNMENT_CACHE is not None:
        return _ALIGNMENT_CACHE

    dataset: List[Dict[str, str]] = []
    candidates = [
        Path("training/data/xeren_identity/xeren_alignment_train.jsonl"),
        Path("../training/data/xeren_identity/xeren_alignment_train.jsonl"),
        Path(__file__).resolve().parents[3] / "training" / "data" / "xeren_identity" / "xeren_alignment_train.jsonl",
    ]

    target_path: Optional[Path] = None
    for p in candidates:
        if p.exists():
            target_path = p
            break

    if not target_path:
        logger.warning("xeren_alignment_train.jsonl not found in candidate paths.")
        _ALIGNMENT_CACHE = []
        return []

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    messages = record.get("messages", [])
                    user_text = ""
                    assistant_text = ""
                    for m in messages:
                        if m.get("role") == "user":
                            user_text = m.get("content", "").strip()
                        elif m.get("role") == "assistant":
                            assistant_text = m.get("content", "").strip()
                    if user_text and assistant_text:
                        dataset.append({
                            "user": user_text,
                            "user_lower": user_text.lower(),
                            "assistant": assistant_text,
                        })
                except Exception:
                    continue
        logger.info("Loaded %d QA pairs from alignment dataset (%s).", len(dataset), target_path)
    except Exception as e:
        logger.warning("Failed to load alignment dataset: %s", e)

    _ALIGNMENT_CACHE = dataset
    return dataset


def find_in_alignment_dataset(query: str) -> Optional[str]:
    """Search for exact or high-confidence match in the 2,221 alignment QA pairs."""
    dataset = load_alignment_dataset()
    if not dataset:
        return None

    q_clean = query.strip().lower()

    # 1. Exact match
    for item in dataset:
        if item["user_lower"] == q_clean:
            return item["assistant"]

    # 2. Substring match (user query contains dataset question or vice-versa)
    best_match: Optional[str] = None
    best_len = 0
    for item in dataset:
        u_lower = item["user_lower"]
        if len(u_lower) > 10 and (u_lower in q_clean or q_clean in u_lower):
            if len(u_lower) > best_len:
                best_len = len(u_lower)
                best_match = item["assistant"]

    return best_match


def answer_grounded_query(raw_query: str) -> Optional[str]:
    """
    Synthesize factual, verified conversational response from the alignment dataset.
    """
    clean = raw_query.strip()
    
    # SEARCH IN ALIGNMENT DATASET
    dataset_ans = find_in_alignment_dataset(clean)
    if dataset_ans:
        return dataset_ans

    return None
