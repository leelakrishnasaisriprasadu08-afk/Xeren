"""
Build Training Dataset for Xeren ToolCaller (Work Assigner & Output Verifier)
=============================================================================
Inspired by JEPA / Discriminator / Fast Evaluator architectures:
1. ZERO Conversational Filler: No pleasantries or natural language chit-chat.
2. Phase 1 - Work Assigner Trajectories:
   - Target specialist routing, strict actions, structured arguments, and verification expectations.
   - High-precision assignment confidence [0.0 - 1.0] and execution strategy.
3. Phase 2 - Output Verifier Trajectories:
   - Evaluates deliverables against expectations.
   - Outputs boolean flags (passed, expectations_met, has_error, syntax_valid, needs_retry)
     and verification confidence scores.
"""

import json
from pathlib import Path
import random
from typing import Dict, List

OUTPUT_DIR = Path("training/data/set1_control_hub/tool_caller")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "You are Xeren ToolCaller, the deterministic Work Assigner and Output Verifier of the Xeren MoS system.\n"
    "You do not engage in natural language conversation. You operate strictly in two modes:\n"
    "1. ASSIGN: Receive task requirements and output a structured WorkAssignmentPlan (targets, expectations, confidence).\n"
    "2. VERIFY: Evaluate specialist outputs against expectations, returning boolean flags (passed, expectations_met, syntax_valid, needs_retry) and confidence scores."
)

ASSIGN_TEMPLATES = [
    (
        "Implement a binary search algorithm in Python with unit tests",
        {
            "phase": "assign",
            "is_executable": True,
            "confidence": 0.985,
            "execution_strategy": "sequential",
            "assignments": [
                {
                    "specialist_id": "M7_coding",
                    "action": "implement_code",
                    "arguments": {"language": "python", "task": "binary search with unit tests"},
                    "expectation": {"format": "code", "syntax_check": True, "non_empty": True}
                }
            ]
        }
    ),
    (
        "Analyze this database query plan and rewrite with optimal index usage",
        {
            "phase": "assign",
            "is_executable": True,
            "confidence": 0.970,
            "execution_strategy": "parallel",
            "assignments": [
                {
                    "specialist_id": "M5_analysis",
                    "action": "analyze_query_plan",
                    "arguments": {"focus": "index and table scans"},
                    "expectation": {"format": "json", "required_keys": ["bottlenecks"], "syntax_check": True}
                },
                {
                    "specialist_id": "M7_coding",
                    "action": "rewrite_query",
                    "arguments": {"optimization": "indexed_join"},
                    "expectation": {"format": "code", "syntax_check": True, "non_empty": True}
                }
            ]
        }
    ),
    (
        "Solve this game theory problem and mathematically verify uniqueness of Nash equilibrium",
        {
            "phase": "assign",
            "is_executable": True,
            "confidence": 0.990,
            "execution_strategy": "sequential",
            "assignments": [
                {
                    "specialist_id": "M2_reasoning",
                    "action": "deduce_equilibrium",
                    "arguments": {"type": "game_theory"},
                    "expectation": {"format": "text", "non_empty": True}
                },
                {
                    "specialist_id": "M10_verification",
                    "action": "verify_uniqueness",
                    "arguments": {"proof_type": "formal"},
                    "expectation": {"format": "json", "required_keys": ["is_unique"], "syntax_check": True}
                }
            ]
        }
    )
]

VERIFY_TEMPLATES = [
    # Compliant Python code -> Pass
    (
        "Verify deliverable for task 'M7_coding': def binary_search(arr, x): ...",
        {
            "phase": "verify",
            "specialist_id": "M7_coding",
            "passed": True,
            "expectations_met": True,
            "confidence": 0.994,
            "has_error": False,
            "syntax_valid": True,
            "needs_retry": False,
            "score": 1.0,
            "error_type": None
        }
    ),
    # Syntax error in Python -> Fail with retry
    (
        "Verify deliverable for task 'M7_coding': def broken_syntax(x\n    return x",
        {
            "phase": "verify",
            "specialist_id": "M7_coding",
            "passed": False,
            "expectations_met": False,
            "confidence": 0.988,
            "has_error": True,
            "syntax_valid": False,
            "needs_retry": True,
            "score": 0.2,
            "error_type": "SYNTAX_ERROR",
            "retry_adjustments": {"fix_syntax": "missing closing parenthesis on def line"}
        }
    ),
    # Broken JSON output -> Fail
    (
        "Verify deliverable for task 'M5_analysis': plain text output without expected json keys",
        {
            "phase": "verify",
            "specialist_id": "M5_analysis",
            "passed": False,
            "expectations_met": False,
            "confidence": 0.975,
            "has_error": True,
            "syntax_valid": False,
            "needs_retry": True,
            "score": 0.1,
            "error_type": "INVALID_JSON"
        }
    ),
    # Valid analysis json -> Pass
    (
        "Verify deliverable for task 'M5_analysis': {\"bottlenecks\": [\"table_scan\"], \"cost\": 120}",
        {
            "phase": "verify",
            "specialist_id": "M5_analysis",
            "passed": True,
            "expectations_met": True,
            "confidence": 0.992,
            "has_error": False,
            "syntax_valid": True,
            "needs_retry": False,
            "score": 1.0,
            "error_type": None
        }
    )
]


def generate_dual_dataset(num_train: int = 900, num_val: int = 150):
    random.seed(42)
    samples = []

    # 1. Expand Assignment Trajectories
    for q, payload in ASSIGN_TEMPLATES:
        for i in range(150):
            prompt = f"[MODE: ASSIGN] User Task #{i+1}: {q}"
            samples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": json.dumps(payload, indent=2)}
                ]
            })

    # 2. Expand Verification Trajectories
    for input_text, verdict in VERIFY_TEMPLATES:
        for i in range(150):
            prompt = f"[MODE: VERIFY] Specimen #{i+1}: {input_text}"
            samples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": json.dumps(verdict, indent=2)}
                ]
            })

    random.shuffle(samples)
    train_samples = samples[:num_train]
    val_samples = samples[num_train:num_train + num_val]

    train_path = OUTPUT_DIR / "train.jsonl"
    val_path = OUTPUT_DIR / "val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(s) + "\n")

    print(f"ToolCaller Dual Assigner & Verifier dataset generated:")
    print(f"  Train: {len(train_samples)} samples ({(train_path.stat().st_size / 1e6):.2f} MB) -> {train_path}")
    print(f"  Val:   {len(val_samples)} samples ({(val_path.stat().st_size / 1e6):.2f} MB) -> {val_path}")


if __name__ == "__main__":
    generate_dual_dataset()
