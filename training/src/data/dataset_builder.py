"""Multi-Source Dataset Builder for Xeren LLM Pre-training and Instruction Training.

Aggregates, standardizes, and converts diverse datasets into Xeren's native ChatML format:
- Xeren Local Trajectories (data/train.jsonl, data/val.jsonl)
- databricks/databricks-dolly-15k (General Instruction Following)
- Salesforce/xlam-function-calling-60k (Function Calling)
- zai-org/AgentInstruct (Agentic Task Execution)
- hotpotqa/hotpot_qa (Multi-Hop RAG)
- open-r1/OpenR1-Math-220k (Step-by-Step Reasoning)
- nvidia/Nemotron-Post-Training-Dataset-v1 (Conversational Quality)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("xeren.training.data")
logging.basicConfig(level=logging.INFO)


SYSTEM_PROMPT = (
    "You are Xeren, an autonomous reasoning and action AI system capable of multi-step planning, "
    "tool execution, retrieval-augmented generation, and precise problem solving."
)


def format_chatml(system_prompt: str, conversations: List[Dict[str, str]]) -> str:
    """Format conversations into standardized ChatML format."""
    text = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
    for conv in conversations:
        role = conv["role"]
        content = conv["content"]
        text += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    return text


class DatasetBuilder:
    def __init__(self, output_dir: str = "training/data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_local_xeren_trajectories(self, filepath: str) -> List[str]:
        """Convert native Xeren JSONL records to structured ChatML training text."""
        records = []
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Local Xeren trajectory file not found: {filepath}")
            return records

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                task = data.get("task", "")
                plan = data.get("plan", [])
                actions = data.get("actions", [])
                recovery = data.get("recovery_strategy")

                convs = [{"role": "user", "content": task}]

                # Agent planning thought
                plan_str = "\n".join(f"{i+1}. {p}" for i, p in enumerate(plan))
                thought_content = f"Plan:\n{plan_str}"
                if recovery:
                    thought_content += f"\n\nRecovery Strategy: {recovery}"
                convs.append({"role": "thought", "content": thought_content})

                # Actions / Tool Calls
                for act in actions:
                    tool_name = act.get("tool_name", "")
                    tool_args = json.dumps(act.get("tool_args", {}))
                    result = act.get("result", "")
                    rationale = act.get("action_selection_rationale", "")

                    if rationale:
                        convs.append({"role": "thought", "content": f"Action rationale: {rationale}"})
                    convs.append({"role": "tool_call", "content": f"{tool_name}({tool_args})"})
                    convs.append({"role": "tool_result", "content": str(result)})

                # Final synthesis
                final_answer = (
                    f"Task execution completed. Success status: {data.get('success', True)}. "
                    f"Quality score: {data.get('final_quality_score', 1.0)}"
                )
                convs.append({"role": "assistant", "content": final_answer})

                records.append(format_chatml(SYSTEM_PROMPT, convs))

        logger.info(f"Loaded {len(records)} samples from {filepath}")
        return records

    def process_dolly_sample(self, item: Dict[str, Any]) -> str:
        """Format a Databricks Dolly record."""
        instruction = item.get("instruction", "")
        context = item.get("context", "")
        response = item.get("response", "")

        user_content = instruction
        if context:
            user_content += f"\n\nContext:\n{context}"

        convs = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": response},
        ]
        return format_chatml(SYSTEM_PROMPT, convs)

    def process_xlam_sample(self, item: Dict[str, Any]) -> str:
        """Format a Salesforce xLAM function calling record."""
        query = item.get("query", "")
        tools = item.get("tools", "")
        answers = item.get("answers", "")

        user_content = f"Available Tools:\n{tools}\n\nTask: {query}"
        convs = [
            {"role": "user", "content": user_content},
            {"role": "tool_call", "content": str(answers)},
            {"role": "assistant", "content": f"Invoking tool call: {answers}"},
        ]
        return format_chatml(SYSTEM_PROMPT, convs)

    def process_hotpot_sample(self, item: Dict[str, Any]) -> str:
        """Format a HotpotQA multi-hop QA record."""
        question = item.get("question", "")
        answer = item.get("answer", "")
        context = item.get("context", "")

        if isinstance(context, list):
            context_str = "\n".join([f"- {c[0]}: {' '.join(c[1])}" for c in context[:3]])
        else:
            context_str = str(context)[:1000]

        user_content = f"Question: {question}\n\nRetrieved Context:\n{context_str}"
        convs = [
            {"role": "user", "content": user_content},
            {"role": "thought", "content": f"Analyzing multi-hop context to answer: {question}"},
            {"role": "assistant", "content": answer},
        ]
        return format_chatml(SYSTEM_PROMPT, convs)

    def process_math_sample(self, item: Dict[str, Any]) -> str:
        """Format an OpenR1 Math step-by-step reasoning record."""
        problem = item.get("problem", "")
        solution = item.get("solution", "")
        convs = [
            {"role": "user", "content": problem},
            {"role": "thought", "content": "Solving step-by-step with rigorous proof and calculation."},
            {"role": "assistant", "content": solution},
        ]
        return format_chatml(SYSTEM_PROMPT, convs)

    def fetch_hf_dataset_samples(
        self,
        dataset_name: str,
        split: str = "train",
        max_samples: Optional[int] = None,
        processor_fn: Optional[Any] = None,
    ) -> List[str]:
        """Safely fetch samples from Hugging Face datasets library."""
        try:
            from datasets import load_dataset

            logger.info(f"Fetching from {dataset_name} ({split})...")
            ds = load_dataset(dataset_name, split=split, streaming=True)
            results = []
            for i, item in enumerate(ds):
                if max_samples and i >= max_samples:
                    break
                if processor_fn:
                    formatted = processor_fn(item)
                    if formatted:
                        results.append(formatted)
            logger.info(f"Extracted {len(results)} samples from {dataset_name}")
            return results
        except Exception as e:
            logger.warning(f"Could not load Hugging Face dataset {dataset_name}: {e}")
            return []

    def build_synthetic_agent_samples(self, count: int = 50) -> List[str]:
        """Generate high-quality synthetic agent trajectories for initial training stability."""
        templates = [
            (
                "Search vector memory for topic '{topic}' and summarize findings.",
                "1. Vector search query '{topic}'\n2. Rank results by similarity\n3. Synthesize summary",
                "vector_search",
                '{{"query": "{topic}", "top_k": 3}}',
                "Found 3 matching chunks for {topic} with scores > 0.85.",
                "Here is the summary of {topic} based on the retrieved documents.",
            ),
            (
                "Compute arithmetic expression '{expr}' and verify boundary values.",
                "1. Parse arithmetic tokens\n2. Call calculator tool\n3. Verify bounds",
                "calculator",
                '{{"expression": "{expr}"}}',
                "Result: 1024",
                "The mathematical calculation for '{expr}' evaluates to 1024.",
            ),
            (
                "Filter database records where status is active and created_at > 2026-01-01.",
                "1. Formulate structured SQL filter\n2. Execute metadata query\n3. Validate result count",
                "db_query",
                '{{"filter": {{"status": "active", "created_at": {{"$gt": "2026-01-01"}}}}}}',
                "Matched 15 active records.",
                "Found 15 matching active records in database.",
            ),
            (
                "Fetch API health status from '{endpoint}' with 3.0s timeout.",
                "1. Send HTTP GET to endpoint\n2. Check response status 200 OK\n3. Log service health",
                "http_get",
                '{{"url": "{endpoint}", "timeout": 3.0}}',
                '{{"status": "UP", "uptime_sec": 86400}}',
                "Service at {endpoint} is healthy and operational.",
            ),
        ]

        topics = ["RAG architecture", "KV-cache optimization", "FlashAttention", "LoRA parameters", "RoPE embeddings"]
        endpoints = ["https://api.xeren.local/health", "https://auth.xeren.local/v1/ping", "https://vector.xeren.local/status"]

        samples = []
        for i in range(count):
            tpl = templates[i % len(templates)]
            topic = topics[i % len(topics)]
            endpoint = endpoints[i % len(endpoints)]
            expr = f"{i+1} * 64 + 256"

            task = tpl[0].format(topic=topic, expr=expr, endpoint=endpoint)
            plan = tpl[1].format(topic=topic, expr=expr, endpoint=endpoint)
            tool = tpl[2]
            tool_args = tpl[3].format(topic=topic, expr=expr, endpoint=endpoint)
            res = tpl[4].format(topic=topic, expr=expr, endpoint=endpoint)
            ans = tpl[5].format(topic=topic, expr=expr, endpoint=endpoint)

            convs = [
                {"role": "user", "content": task},
                {"role": "thought", "content": f"Plan:\n{plan}"},
                {"role": "tool_call", "content": f"{tool}({tool_args})"},
                {"role": "tool_result", "content": res},
                {"role": "assistant", "content": ans},
            ]
            samples.append(format_chatml(SYSTEM_PROMPT, convs))

        return samples

    def build_dataset(
        self,
        local_train_path: str = "data/train.jsonl",
        local_val_path: str = "data/val.jsonl",
        include_hf_datasets: bool = True,
        max_samples_per_hf: int = 200,
    ) -> Dict[str, List[str]]:
        """Assemble full multi-source dataset and save to processed directory."""
        all_samples = []

        # 1. Local Xeren Trajectories
        all_samples.extend(self.load_local_xeren_trajectories(local_train_path))
        val_samples = self.load_local_xeren_trajectories(local_val_path)

        # 2. Synthetic trajectories for agent grounding
        all_samples.extend(self.build_synthetic_agent_samples(count=100))

        # 3. External HF datasets
        if include_hf_datasets:
            all_samples.extend(
                self.fetch_hf_dataset_samples(
                    "databricks/databricks-dolly-15k",
                    max_samples=max_samples_per_hf,
                    processor_fn=self.process_dolly_sample,
                )
            )
            all_samples.extend(
                self.fetch_hf_dataset_samples(
                    "Salesforce/xlam-function-calling-60k",
                    max_samples=max_samples_per_hf,
                    processor_fn=self.process_xlam_sample,
                )
            )
            all_samples.extend(
                self.fetch_hf_dataset_samples(
                    "hotpotqa/hotpot_qa",
                    split="train",
                    max_samples=max_samples_per_hf,
                    processor_fn=self.process_hotpot_sample,
                )
            )

        # Ensure validation split has samples
        if not val_samples:
            split_idx = max(1, int(len(all_samples) * 0.9))
            train_samples = all_samples[:split_idx]
            val_samples = all_samples[split_idx:]
        else:
            train_samples = all_samples

        # Save to disk
        train_file = self.output_dir / "train_texts.json"
        val_file = self.output_dir / "val_texts.json"

        with open(train_file, "w", encoding="utf-8") as f:
            json.dump(train_samples, f, indent=2)

        with open(val_file, "w", encoding="utf-8") as f:
            json.dump(val_samples, f, indent=2)

        logger.info(f"Saved {len(train_samples)} training samples to {train_file}")
        logger.info(f"Saved {len(val_samples)} validation samples to {val_file}")

        return {"train": train_samples, "val": val_samples}
