"""Royal Triumvirate Trajectory Synthesizer & Dataset Engine.

Generates high-fidelity training samples teaching the 3-role leadership loop:
  1. King intent understanding & user conveyance.
  2. Advisor Chain-of-Thought (<think>) strategic reasoning.
  3. Commander deterministic tool vs. micro-bot dispatch.
  4. Final King sovereign deliverable synthesis.
  5. DPO preference pairs (Chosen verified execution vs Rejected hallucinated/destructive execution).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xeren.core.leadership import default_triumvirate

logger = logging.getLogger("xeren.data.synthesizer")


class TriumvirateTrajectorySynthesizer:
    """Produces verified ChatML, SFT, and DPO datasets for fine-tuning the 3 models."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or Path("training/data/triumvirate")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.triumvirate = default_triumvirate

    def create_sample(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        custom_deliverable: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete 4-stage Triumvirate trajectory."""
        counsel = self.triumvirate.consult_advisor(task, context)
        decree = self.triumvirate.issue_decree(task, counsel, context)
        report = self.triumvirate.execute_commander(decree, counsel)
        if custom_deliverable:
            report.deliverable = custom_deliverable
        response = self.triumvirate.synthesize_outcome(task, decree, counsel, report)

        # Standard ChatML conversation format for fine-tuning the King
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Xeren, a sovereign, autonomous AI workstation. "
                    "You rule as the King: making strategic decisions, consulting the Advisor for deep reasoning, "
                    "commanding micro-bots and deterministic tools, and delivering precise, verified results to the user."
                ),
            },
            {"role": "user", "content": task},
            {
                "role": "assistant",
                "content": f"{counsel.reasoning_trace}\n\n{response.content}",
            },
        ]

        return {
            "task": task,
            "counsel": counsel.model_dump(),
            "decree": decree.model_dump(),
            "report": report.model_dump(),
            "response": response.model_dump(),
            "messages": messages,
        }

    def create_dpo_pair(self, task: str) -> Dict[str, Any]:
        """Generate a Direct Preference Optimization (DPO) chosen vs rejected pair."""
        sample = self.create_sample(task)
        counsel = sample["counsel"]
        response = sample["response"]

        chosen = f"{counsel['reasoning_trace']}\n\n{response['content']}"

        # Synthesize a rejected alternative: hallucinated, careless, or leaking internal models
        rejected = (
            f"I am an AI assistant powered by OpenAI and Meta models. "
            f"I have automatically completed your task '{task}' without checking files or verifying syntax. "
            f"Here is a generic answer without testing or checking edge cases."
        )

        return {
            "prompt": task,
            "chosen": chosen,
            "rejected": rejected,
            "domain": counsel.get("deterministic_action") or "agentic_multibot",
            "is_purely_deterministic": counsel.get("is_purely_deterministic", False),
        }

    def export_sft_dataset(self, tasks: List[str], filename: str = "triumvirate_sft.jsonl") -> Path:
        """Synthesize and export a batch of SFT trajectories to JSONL."""
        out_path = self.output_dir / filename
        samples = []
        for t in tasks:
            s = self.create_sample(t)
            samples.append(s)

        with open(out_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        logger.info("Exported %d Triumvirate SFT samples to %s", len(samples), out_path)
        return out_path

    # Backwards compatibility alias
    export_dataset = export_sft_dataset

    def export_dpo_dataset(self, tasks: List[str], filename: str = "triumvirate_dpo.jsonl") -> Path:
        """Synthesize and export a batch of DPO preference pairs to JSONL."""
        out_path = self.output_dir / filename
        pairs = []
        for t in tasks:
            p = self.create_dpo_pair(t)
            pairs.append(p)

        with open(out_path, "w", encoding="utf-8") as f:
            for p in pairs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

        logger.info("Exported %d Triumvirate DPO pairs to %s", len(pairs), out_path)
        return out_path

    def export_complete_dataset(self, tasks: List[str]) -> Dict[str, Any]:
        """Synthesize both SFT and DPO splits, generating a comprehensive dataset manifest."""
        sft_path = self.export_sft_dataset(tasks, "triumvirate_sft.jsonl")
        dpo_path = self.export_dpo_dataset(tasks, "triumvirate_dpo.jsonl")

        manifest = {
            "dataset_name": "xeren_royal_triumvirate_v1",
            "total_tasks": len(tasks),
            "sft_file": str(sft_path),
            "dpo_file": str(dpo_path),
            "roles_covered": ["The King (Xeren)", "The Advisor (DeepSeek-R1)", "The Commander (Empower)"],
            "clusters_represented": ["coding", "research", "os", "security", "deterministic"],
        }
        manifest_path = self.output_dir / "dataset_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest


# Rich task library covering all 5 core operational domains
EXPANDED_FOUNDATIONAL_TASKS = [
    # 1. Local Files & Code Management (Deterministic First)
    "Read the contents of README.md and summarize the architecture",
    "List all files in the current workspace directory",
    "Inspect the local laptop system specs and operating system version",
    "Open a browser tab to https://github.com",
    "Read the database configuration file and check active ports",
    "Find all Python files in the src directory that contain leadership models",
    "Patch the database configuration file to update port 5432 to 5433",
    "List all markdown files in the docs directory",
    "Inspect CPU and memory utilization on the local machine",
    "Open the default notepad application on the laptop",

    # 2. Software Engineering & Micro-Bots (M7 Coding Cluster)
    "Build a modern responsive navigation bar using React and Tailwind CSS",
    "Create a React component for user profile settings with status toggle",
    "Construct a typed FastAPI router for managing customer orders",
    "Formulate an indexed PostgreSQL schema for user authentication logs",
    "Verify the syntax and imports of all recently modified Python files",
    "Generate a cyber-glass panel container using Tailwind CSS",
    "Build an interactive React button with tactile scale transitions",
    "Create a FastAPI endpoint to upload and validate CSV datasets",
    "Optimize a slow SQL join across users and transaction tables",
    "Lint and check AST validity for the payment processing script",

    # 3. Grounded Deep Research (M4 Research Cluster)
    "Research the principles of quantum key distribution from verified sources",
    "Generate 3 targeted search angles for room-temperature superconductors",
    "Clean and strip HTML boilerplate from documentation web pages",
    "Summarize the architectural differences between GGUF and AWQ quantization",
    "Verify the empirical benchmark claims for 1.5B language models",
    "Formulate academic citations for multi-agent reinforcement learning papers",
    "Research zero-latency local voice engines comparing Whisper and Piper",
    "Synthesize the trade-offs between local vector stores and relational search",
    "Extract key technical insights from the latest Qwen2.5-Coder benchmark",
    "Cross-verify claim: 'DeepSeek-R1 uses reinforcement learning without supervised warm-up'",

    # 4. Security, Ethics & Safety (M14 Guard Cluster)
    "Intercept and block dangerous commands like format c: or rm -rf /",
    "Sanitize chat logs by redacting API keys and passwords",
    "Zero session memory buffers after processing sensitive user documents",
    "Validate that file writes remain strictly contained within approved project roots",
    "Record immutable audit logs for system configuration changes",

    # 5. Hybrid Online Fallback (Heavy Cloud Offload)
    "Generate 3D model GLTF asset with raytracing for product showcase",
    "Render 4K video animation for landing page hero background",
    "Execute heavy CUDA matrix computation exceeding local VRAM capacity",
    "Deploy full-stack project to remote cloud AWS cluster",
    "Query proprietary live stock ticker websocket via cloud bridge",
]

FOUNDATIONAL_TASKS = EXPANDED_FOUNDATIONAL_TASKS


FOUNDATIONAL_TASKS = EXPANDED_FOUNDATIONAL_TASKS

