"""Automated Capability Benchmark Verification for Xeren 214M LLM.

Tests model generations across the core test matrix:
1. Xeren Identity & System Persona
2. General Knowledge & Multi-Turn Coherence
3. Step-by-Step Arithmetic Reasoning
4. Python Programming & Syntax Validity
5. RAG & Retrieval Architecture Explanation
6. Structured JSON Tool Dispatch
7. Agent Multi-Step Planning
8. Security & Verification

Usage:
  # Test the newly matured checkpoint
  python training/scripts/verify_matured_benchmarks.py

  # Compare Stage-1 Base vs Stage-1 Matured side-by-side
  python training/scripts/verify_matured_benchmarks.py --compare_base
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import torch

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.src.inference.generate import XerenGenerator
from training.src.model.config import XerenConfig
from training.src.model.xeren_transformer import XerenTransformer
from training.src.tokenizer.train_tokenizer import XerenTokenizer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("xeren_benchmarks")

DEFAULT_SYSTEM_PROMPT = (
    "You are Xeren, an autonomous reasoning and action AI system capable of "
    "multi-step planning, tool execution, retrieval-augmented generation, and precise problem solving."
)

BENCHMARK_TESTS = [
    {
        "id": "identity",
        "category": "Xeren Identity & Architecture",
        "prompt": "What is Xeren and what are the core components of your architecture?",
        "max_new_tokens": 120,
    },
    {
        "id": "general_knowledge",
        "category": "General Knowledge & Conversation",
        "prompt": "What is the capital of France and what is it famous for?",
        "max_new_tokens": 80,
    },
    {
        "id": "arithmetic",
        "category": "Arithmetic Reasoning",
        "prompt": "What is 45 + 78? Show your step-by-step calculation.",
        "max_new_tokens": 80,
    },
    {
        "id": "python_code",
        "category": "Python Programming",
        "prompt": "Write a Python function to reverse a string and explain how it works.",
        "max_new_tokens": 100,
    },
    {
        "id": "rag_explanation",
        "category": "RAG & Retrieval Architecture",
        "prompt": "How does the RAG pipeline in Xeren index documents and retrieve relevant chunks?",
        "max_new_tokens": 120,
    },
    {
        "id": "tool_dispatch",
        "category": "Tool Usage & JSON Dispatch",
        "prompt": "Dispatch a JSON tool call to list all files in the directory 'training/src'.",
        "max_new_tokens": 100,
    },
    {
        "id": "agent_planning",
        "category": "Agent Multi-Step Planning",
        "prompt": "Provide a numbered execution plan to inspect, test, and deploy a Python package.",
        "max_new_tokens": 120,
    },
    {
        "id": "security",
        "category": "Security & Verification",
        "prompt": "How does Xeren ensure safe execution of code and prevent malicious actions?",
        "max_new_tokens": 100,
    },
]


def load_model(checkpoint_path: Path, device: torch.device) -> XerenTransformer:
    """Load model from checkpoint dictionary."""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    ckpt = torch.load(str(checkpoint_path), map_location=device)
    config = XerenConfig(**ckpt["config"])
    model = XerenTransformer(config).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def format_prompt(user_text: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    """Format single-turn user prompt into Xeren ChatML string."""
    return (
        f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
        f"<|im_start|>user\n{user_text}\n<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def clean_output(generated_text: str) -> str:
    """Strip system and user prefixes, returning assistant response."""
    if "<|im_start|>assistant" in generated_text:
        res = generated_text.split("<|im_start|>assistant")[-1]
        res = res.replace("<|im_end|>", "").strip()
        if res.startswith("\n"):
            res = res[1:].strip()
        return res
    return generated_text.strip()


def run_benchmarks(
    checkpoint_path: str,
    tokenizer_path: str,
    device_name: str = "cuda:0",
    temperature: float = 0.3,
    repetition_penalty: float = 1.25,
) -> Dict[str, Any]:
    """Execute all benchmark tests on the target checkpoint."""
    device = torch.device(device_name if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    tok = XerenTokenizer.load(tokenizer_path)
    model = load_model(Path(checkpoint_path), device)
    generator = XerenGenerator(model, tok, device=str(device))

    results = []
    print("\n" + "=" * 75)
    print(f"RUNNING XEREN CAPABILITY BENCHMARKS")
    print(f"Checkpoint : {checkpoint_path}")
    print(f"Device     : {device}")
    print("=" * 75)

    for idx, test in enumerate(BENCHMARK_TESTS, 1):
        prompt = format_prompt(str(test["prompt"]))
        t0 = time.time()
        raw_output = generator.generate(
            prompt,
            max_new_tokens=int(test["max_new_tokens"]),
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        )
        elapsed = time.time() - t0
        cleaned = clean_output(raw_output)

        print(f"\n[{idx}/8] Category: {test['category']}")
        print(f"Prompt    : {test['prompt']}")
        print("-" * 50)
        print(f"Response  :\n{cleaned}")
        print(f"(Latency: {elapsed:.2f}s)")
        print("-" * 75)

        results.append({
            "id": test["id"],
            "category": test["category"],
            "prompt": test["prompt"],
            "response": cleaned,
            "latency_seconds": round(elapsed, 2),
        })

    return {
        "checkpoint": checkpoint_path,
        "device": str(device),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Xeren Capability Benchmarks")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="training/checkpoints/stage1_matured/checkpoint_final.pt",
        help="Path to checkpoint file",
    )
    parser.add_argument(
        "--base_checkpoint",
        type=str,
        default="training/checkpoints/stage1/checkpoint_final.pt",
        help="Path to original base checkpoint for comparison",
    )
    parser.add_argument(
        "--tokenizer",
        type=str,
        default="training/checkpoints/tokenizer_32k",
        help="Path to tokenizer directory",
    )
    parser.add_argument("--compare_base", action="store_true", help="Compare against base checkpoint")
    parser.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature")
    parser.add_argument("--repetition_penalty", type=float, default=1.25, help="Repetition penalty")
    parser.add_argument("--device", type=str, default="cuda:0", help="Compute device")

    args = parser.parse_args()

    # Fallback to checkpoint_pilot.pt if checkpoint_final.pt does not exist
    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        alt = Path("training/checkpoints/stage1_matured/checkpoint_pilot.pt")
        if alt.exists():
            ckpt_path = alt

    matured_results = run_benchmarks(
        str(ckpt_path),
        args.tokenizer,
        device_name=args.device,
        temperature=args.temperature,
        repetition_penalty=args.repetition_penalty,
    )

    out_file = Path("training/checkpoints/stage1_matured/benchmark_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(matured_results, f, indent=2)
    print(f"\n[OK] Saved benchmark results to: {out_file}\n")


if __name__ == "__main__":
    main()
