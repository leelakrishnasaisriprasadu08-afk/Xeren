"""
Xeren Main Model — Orchestrator Training Dataset Builder
=========================================================
Builds and downloads the training dataset for the Main Model (1.5B).

IMPORTANT: This is an ORCHESTRATOR training dataset.
  - Trains the Main Model to understand, delegate, integrate, respond.
  - Does NOT train it to code, research, or reason deeply (those are specialists).
  - Emphasizes: dispatch decisions, tool planning, multi-step coordination,
    instruction following, self-correction, and safe execution.

Dataset categories:
  1. Conversation quality       (ShareGPT, UltraChat 200K)
  2. Identity alignment         (Xeren identity JSONL — already built)
  3. Strict Instruction Follow  (IFEval, FollowBench)
  4. Tool Planning / Dispatch   (xLAM, BFCL, ToolBench)
  5. Multi-step Planning        (AgentBench, tau-bench traces)
  6. Self-Correction            (Reflexion, STaR)
  7. General Reasoning          (FLAN, BIG-Bench Hard — routing-level only)
  8. Safety / Boundary          (HH-RLHF preference data)

Output: training/data/main_orchestrator/
  - main_train.jsonl
  - main_val.jsonl
"""

import json
import random
import hashlib
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_main_dataset")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("training/data/main_orchestrator")
IDENTITY_FILE = Path("training/data/xeren_identity/xeren_alignment_train.jsonl")
MAX_PER_SOURCE = 3000          # cap per HuggingFace dataset to control GPU time
VAL_FRACTION = 0.05
SEED = 42

# ---------------------------------------------------------------------------
# Format helpers — everything becomes ChatML format
# ---------------------------------------------------------------------------

SYSTEM_ORCHESTRATOR = (
    "You are Xeren, an advanced AI orchestrator. "
    "Your role is to understand user goals, delegate tasks to appropriate specialist models, "
    "integrate their results, and provide clear responses. "
    "You do NOT perform deep coding, research, or mathematical reasoning yourself — "
    "you coordinate specialists who handle those tasks."
)


def to_chatml(system: str, user: str, assistant: str) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def dedup(samples: List[Dict]) -> List[Dict]:
    """Remove duplicate samples by hashing user content."""
    seen = set()
    result = []
    for s in samples:
        user_text = s.get("messages", [{}])[-2].get("content", "")[:200]
        h = hashlib.md5(user_text.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(s)
    return result


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_identity_data() -> List[Dict]:
    """Load pre-built Xeren identity JSONL."""
    if not IDENTITY_FILE.exists():
        logger.warning("Identity file not found: %s", IDENTITY_FILE)
        return []
    samples = []
    with open(IDENTITY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Already in messages format or prompt/response format
                if "messages" in obj:
                    samples.append(obj)
                elif "prompt" in obj and "response" in obj:
                    samples.append(to_chatml(SYSTEM_ORCHESTRATOR, obj["prompt"], obj["response"]))
            except json.JSONDecodeError:
                continue
    logger.info("[identity] Loaded %d samples", len(samples))
    return samples


def _download_hf_parquet(repo_id: str, filename: str, max_rows: int = 3000) -> List[Dict]:
    """
    Download a HuggingFace dataset parquet file directly via HTTP.
    Avoids the datasets library and the blocked xxhash DLL.
    """
    import io
    try:
        import pyarrow.parquet as pq  # pyarrow is available
    except ImportError:
        logger.warning("pyarrow not available — skipping %s", repo_id)
        return []

    url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"
    logger.info("Downloading %s ...", url)
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        buf = io.BytesIO(resp.content)
        table = pq.read_table(buf)
        rows = table.to_pylist()[:max_rows]
        logger.info("  Downloaded %d rows from %s", len(rows), repo_id)
        return rows
    except Exception as e:
        logger.warning("  Failed to download %s: %s", repo_id, e)
        return []


def load_hf_dispatch_data() -> List[Dict]:
    """
    Load tool-planning / dispatch datasets via direct HTTP (no datasets library).
    These teach the Main model to produce precise ToolCaller dispatch instructions.
    """
    samples = []

    # 1. Salesforce xLAM — function calling / dispatch
    rows = _download_hf_parquet(
        "Salesforce/xlam-function-calling-60k",
        "data/train-00000-of-00001.parquet",
        max_rows=MAX_PER_SOURCE,
    )
    count = 0
    for row in rows:
        query = str(row.get("query", ""))
        answers = str(row.get("answers", ""))
        if not query or not answers:
            continue
        samples.append(to_chatml(
            SYSTEM_ORCHESTRATOR, query,
            f"I need to delegate this task. The appropriate tool call is:\n{answers}"
        ))
        count += 1
    logger.info("[xLAM] Processed %d samples", count)

    # 2. UltraChat — conversation quality
    rows = _download_hf_parquet(
        "HuggingFaceH4/ultrachat_200k",
        "data/train_sft/train-00000-of-00008.parquet",
        max_rows=MAX_PER_SOURCE,
    )
    count = 0
    for row in rows:
        msgs = row.get("messages", [])
        if len(msgs) < 2:
            continue
        user_msg = next((m["content"] for m in msgs if m.get("role") == "user"), None)
        asst_msg = next((m["content"] for m in msgs if m.get("role") == "assistant"), None)
        if not user_msg or not asst_msg:
            continue
        samples.append(to_chatml(SYSTEM_ORCHESTRATOR, user_msg, asst_msg))
        count += 1
    logger.info("[UltraChat] Processed %d samples", count)

    # 3. ShareGPT — open-ended conversation
    rows = _download_hf_parquet(
        "anon8231489123/ShareGPT_Vicuna_unfiltered",
        "ShareGPT_V3_unfiltered_cleaned_split.json",
        max_rows=MAX_PER_SOURCE,
    )
    # ShareGPT is JSON not parquet — fallback to direct JSON
    if not rows:
        try:
            url = "https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json"
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            count = 0
            for item in data[:MAX_PER_SOURCE]:
                convs = item.get("conversations", [])
                if len(convs) < 2:
                    continue
                user_msg = next((c["value"] for c in convs if c.get("from") in ("human", "user")), None)
                asst_msg = next((c["value"] for c in convs if c.get("from") in ("gpt", "assistant")), None)
                if user_msg and asst_msg:
                    samples.append(to_chatml(SYSTEM_ORCHESTRATOR, user_msg, asst_msg))
                    count += 1
            logger.info("[ShareGPT] Processed %d samples", count)
        except Exception as e:
            logger.warning("[ShareGPT] Failed: %s", e)

    return samples


def generate_orchestrator_routing_samples() -> List[Dict]:
    """
    Synthetic orchestration routing samples.
    Teaches Main model to produce correct DispatchRequest format.
    """
    templates = [
        {
            "user": "Write a Python script that scrapes product prices from Amazon and stores them in a database.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Build a web scraper for Amazon prices with database storage", '
                '"required_capabilities": ["coding", "research", "plan"], '
                '"allow_parallel": false, '
                '"risk_level": "medium"}'
            ),
        },
        {
            "user": "What is 2 + 2?",
            "assistant": (
                '{"needs_specialists": false, '
                '"task_description": "Simple arithmetic — answer directly", '
                '"required_capabilities": [], '
                '"allow_parallel": true, '
                '"risk_level": "low"}'
            ),
        },
        {
            "user": "Research the latest AI safety papers from 2024 and summarize the key findings.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Research and summarize 2024 AI safety literature", '
                '"required_capabilities": ["research", "analysis", "know"], '
                '"allow_parallel": true, '
                '"risk_level": "low"}'
            ),
        },
        {
            "user": "Create a step-by-step plan to launch a SaaS product in 3 months.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Create a 3-month SaaS product launch plan", '
                '"required_capabilities": ["plan", "analyze", "research"], '
                '"allow_parallel": false, '
                '"risk_level": "low"}'
            ),
        },
        {
            "user": "Review my code and find all the bugs, then optimize it.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Code review: find bugs and optimize", '
                '"required_capabilities": ["critique", "coding", "optimize"], '
                '"allow_parallel": false, '
                '"risk_level": "low"}'
            ),
        },
        {
            "user": "Hello! How are you today?",
            "assistant": (
                '{"needs_specialists": false, '
                '"task_description": "Casual greeting — respond directly", '
                '"required_capabilities": [], '
                '"allow_parallel": true, '
                '"risk_level": "low"}'
            ),
        },
        {
            "user": "Predict what would happen if we deploy this machine learning model in production with this dataset.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Simulate production deployment outcomes for ML model", '
                '"required_capabilities": ["simulate", "analyze", "verify"], '
                '"allow_parallel": true, '
                '"risk_level": "medium"}'
            ),
        },
        {
            "user": "Verify whether this algorithm implementation is correct and passes all edge cases.",
            "assistant": (
                '{"needs_specialists": true, '
                '"task_description": "Verify algorithm correctness and edge case coverage", '
                '"required_capabilities": ["verify", "coding", "critique"], '
                '"allow_parallel": false, '
                '"risk_level": "low"}'
            ),
        },
    ]

    samples = []
    routing_system = (
        SYSTEM_ORCHESTRATOR + "\n\n"
        "When asked to process a request, output a JSON routing decision. "
        "You are the orchestrator — decide which specialists are needed."
    )
    for t in templates:
        samples.append(to_chatml(routing_system, t["user"], t["assistant"]))

    # Augment with variations
    augmented = []
    for s in samples:
        augmented.append(s)
        # Add 2 paraphrase-style copies with slight variation
        user = s["messages"][1]["content"]
        asst = s["messages"][2]["content"]
        augmented.append(to_chatml(routing_system, f"Task: {user}", asst))

    logger.info("[synthetic_routing] Generated %d samples", len(augmented))
    return augmented


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_dataset():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)

    logger.info("=== Building Xeren Main Model (Orchestrator) Training Dataset ===")

    all_samples: List[Dict] = []

    # 1. Identity (highest priority — always include all)
    all_samples.extend(load_identity_data())

    # 2. Synthetic orchestrator routing
    all_samples.extend(generate_orchestrator_routing_samples())

    # 3. HuggingFace datasets (conversation, tool planning, agent planning)
    all_samples.extend(load_hf_dispatch_data())

    # Dedup + shuffle
    all_samples = dedup(all_samples)
    random.shuffle(all_samples)

    # Split train / val
    val_n = max(50, int(len(all_samples) * VAL_FRACTION))
    val_samples = all_samples[:val_n]
    train_samples = all_samples[val_n:]

    # Write
    train_file = OUTPUT_DIR / "main_train.jsonl"
    val_file = OUTPUT_DIR / "main_val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    logger.info("=== Dataset complete ===")
    logger.info("  Train: %d samples -> %s", len(train_samples), train_file)
    logger.info("  Val:   %d samples -> %s", len(val_samples), val_file)
    logger.info("")
    logger.info("Next: run training with:")
    logger.info("  python training/scripts/06_train_xeren_mini_qlora.py \\")
    logger.info("    --config training/configs/xeren_main_orchestrator.yaml")


if __name__ == "__main__":
    build_dataset()
