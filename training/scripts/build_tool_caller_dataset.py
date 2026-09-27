"""
Build Training Dataset for Xeren ToolCaller
===========================================
Generates structured dispatch trajectories for ToolCaller:
- User query / DispatchRequest
- Multi-specialist selection and routing
- Tool calling parameters (function name, arguments, expected output)
- Structured JSON output format: DispatchResponse / function calls
"""

import json
import random
from pathlib import Path
from typing import Dict, List

OUTPUT_DIR = Path("training/data/tool_caller")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "You are Xeren ToolCaller, the deterministic routing and tool dispatch model of the Xeren MoS system.\n"
    "Given a user query or orchestrator task, analyze the required capabilities and output a precise JSON "
    "dispatch specification containing the target specialist(s) and structured parameters."
)

TEMPLATES = [
    # M7 Coding
    (
        "Implement a binary search algorithm in Python with unit tests",
        ["coding"],
        {
            "selected_specialists": ["M7_coding"],
            "strategy": "sequential",
            "calls": [
                {
                    "specialist": "M7_coding",
                    "action": "implement_code",
                    "arguments": {
                        "language": "python",
                        "task": "binary search with unit tests",
                        "include_type_hints": True
                    }
                }
            ]
        }
    ),
    (
        "Refactor this slow database query to use indexing and explain the execution plan",
        ["coding", "analysis", "optimization"],
        {
            "selected_specialists": ["M5_analysis", "M7_coding", "M11_optimization"],
            "strategy": "parallel",
            "calls": [
                {
                    "specialist": "M5_analysis",
                    "action": "analyze_query_plan",
                    "arguments": {"focus": "indexes and table scans"}
                },
                {
                    "specialist": "M7_coding",
                    "action": "rewrite_query",
                    "arguments": {"style": "optimized SQL"}
                },
                {
                    "specialist": "M11_optimization",
                    "action": "benchmark_optimization",
                    "arguments": {"metric": "latency"}
                }
            ]
        }
    ),
    # M2 Reasoning + M10 Verification
    (
        "Solve this logic puzzle and mathematically verify if the solution is unique",
        ["reasoning", "verification"],
        {
            "selected_specialists": ["M2_reasoning", "M10_verification"],
            "strategy": "sequential",
            "calls": [
                {
                    "specialist": "M2_reasoning",
                    "action": "step_by_step_deduction",
                    "arguments": {"show_work": True}
                },
                {
                    "specialist": "M10_verification",
                    "action": "formal_verification",
                    "arguments": {"check_uniqueness": True}
                }
            ]
        }
    ),
    # M4 Research + M3 Knowledge
    (
        "What are the latest discoveries regarding room-temperature superconductivity from 2024 to 2026?",
        ["research", "knowledge"],
        {
            "selected_specialists": ["M4_research", "M3_knowledge"],
            "strategy": "parallel",
            "calls": [
                {
                    "specialist": "M4_research",
                    "action": "search_literature",
                    "arguments": {"query": "room temperature superconductivity papers 2024-2026", "depth": "academic"}
                },
                {
                    "specialist": "M3_knowledge",
                    "action": "retrieve_physics_principles",
                    "arguments": {"topic": "BCS theory and high-Tc mechanisms"}
                }
            ]
        }
    ),
    # M6 Planning + M8 Simulation
    (
        "Plan a high-availability multi-region Kubernetes deployment and simulate network partition failure modes",
        ["planning", "simulation"],
        {
            "selected_specialists": ["M6_planning", "M8_simulation"],
            "strategy": "sequential",
            "calls": [
                {
                    "specialist": "M6_planning",
                    "action": "architectural_blueprint",
                    "arguments": {"architecture": "multi-region k8s"}
                },
                {
                    "specialist": "M8_simulation",
                    "action": "chaos_simulation",
                    "arguments": {"scenario": "split-brain / network partition"}
                }
            ]
        }
    ),
    # M1 Understanding + M9 Critic
    (
        "Review this product requirements document for ambiguities, contradictions, and missing edge cases",
        ["understanding", "critic"],
        {
            "selected_specialists": ["M1_understanding", "M9_critic"],
            "strategy": "sequential",
            "calls": [
                {
                    "specialist": "M1_understanding",
                    "action": "extract_requirements_and_intent",
                    "arguments": {"target": "PRD"}
                },
                {
                    "specialist": "M9_critic",
                    "action": "audit_and_find_weaknesses",
                    "arguments": {"focus": ["ambiguities", "edge cases", "contradictions"]}
                }
            ]
        }
    ),
    # M12 Experience / Learning
    (
        "Look up past execution traces for similar database migration failures and summarize root causes",
        ["experience", "analysis"],
        {
            "selected_specialists": ["M12_experience", "M5_analysis"],
            "strategy": "sequential",
            "calls": [
                {
                    "specialist": "M12_experience",
                    "action": "recall_episodic_memory",
                    "arguments": {"domain": "database_migrations", "outcome": "failure"}
                },
                {
                    "specialist": "M5_analysis",
                    "action": "root_cause_clustering",
                    "arguments": {"aggregate": True}
                }
            ]
        }
    ),
]


def expand_dataset(num_train: int = 1350, num_val: int = 130):
    random.seed(42)
    all_samples = []

    domains = [
        ("Python API microservice with rate limiting", ["coding", "verification"], "M7_coding", "M10_verification"),
        ("Optimize transformer attention KV cache memory consumption", ["coding", "optimization"], "M7_coding", "M11_optimization"),
        ("Audit smart contract code for reentrancy vulnerabilities", ["critic", "verification", "coding"], "M9_critic", "M10_verification"),
        ("Break down user retention drop after v2.0 release", ["analysis", "understanding"], "M5_analysis", "M1_understanding"),
        ("Formulate step-by-step game theory strategy for auction", ["reasoning", "planning"], "M2_reasoning", "M6_planning"),
        ("Fact check recent claims about quantum supremacy benchmark", ["research", "verification"], "M4_research", "M10_verification"),
        ("Simulate high-concurrency order placement spike on e-commerce backend", ["simulation", "analysis"], "M8_simulation", "M5_analysis"),
        ("Synthesize historical precedents of monetary policy shifts", ["knowledge", "research"], "M3_knowledge", "M4_research"),
    ]

    for base_query, caps, spec1, spec2 in domains:
        for variation in range(150):
            q = f"Task #{variation+1}: {base_query}. Ensure high rigor."
            payload = {
                "selected_specialists": [spec1, spec2],
                "strategy": "parallel" if "research" in caps or "analysis" in caps else "sequential",
                "calls": [
                    {"specialist": spec1, "action": f"handle_{caps[0]}", "arguments": {"query": q}},
                    {"specialist": spec2, "action": f"handle_{caps[1]}", "arguments": {"query": q}},
                ]
            }
            sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": json.dumps(payload, indent=2)}
                ]
            }
            all_samples.append(sample)

    for q, caps, payload in TEMPLATES:
        for _ in range(40):
            sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": json.dumps(payload, indent=2)}
                ]
            }
            all_samples.append(sample)

    random.shuffle(all_samples)
    train_samples = all_samples[:num_train]
    val_samples = all_samples[num_train:num_train + num_val]

    train_path = OUTPUT_DIR / "tool_caller_train.jsonl"
    val_path = OUTPUT_DIR / "tool_caller_val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(s) + "\n")

    print(f"ToolCaller dataset generated:")
    print(f"  Train: {len(train_samples)} samples -> {train_path}")
    print(f"  Val:   {len(val_samples)} samples -> {val_path}")


if __name__ == "__main__":
    expand_dataset()
