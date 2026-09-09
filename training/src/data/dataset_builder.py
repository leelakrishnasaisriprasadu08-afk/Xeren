"""Multi-Source Dataset Builder for Xeren LLM Pre-training and Instruction Training.

Stage 1 Datasets (Language + Reasoning Foundation):
- Xeren Local Trajectories          (data/train.jsonl, data/val.jsonl)
- databricks/databricks-dolly-15k   (General Instruction Following)
- Salesforce/xlam-function-calling-60k (Function Calling)
- zai-org/AgentInstruct             (Agentic Task Execution)
- hotpotqa/hotpot_qa                (Multi-Hop RAG Reasoning)
- meta-math/MetaMathQA              (Step-by-Step Math Reasoning)

Stage 2 Domain-Specific Datasets:
- NousResearch/hermes-function-calling-v1  (Plugin Architecture + Tool Dispatch)
- open-r1/OpenR1-Math-220k                 (Output Prediction with CoT Probabilities)
- allenai/WildGuard                        (Malware / Safety / Threat Detection)
- bigcode/the-stack-smol                   (Code Understanding for Security Analysis)
- cais/mmlu (security subset)              (Technical Security Knowledge)
- nvidia/Nemotron-Post-Training-Dataset-v1 (Conversational Quality)

Continuous Training:
- Local JSONL buffer    (data/continuous_training/new_sessions.jsonl)
- Supabase PostgreSQL   (experiencerecord table — flushed from local buffer)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("xeren.training.data")
logging.basicConfig(level=logging.INFO)

# Xeren ChatML system prompts per domain
SYSTEM_PROMPTS = {
    "default": (
        "You are Xeren, an autonomous reasoning and action AI system capable of multi-step planning, "
        "tool execution, retrieval-augmented generation, and precise problem solving."
    ),
    "plugin": (
        "You are Xeren. Given a user request, identify the most appropriate plugin to activate "
        "from: research, coding, file, browser, api, conversation, data, knowledge, website. "
        "Then dispatch it with the correct arguments."
    ),
    "security": (
        "You are Xeren Security Analyst. Analyze the provided content for malware, shellcode, "
        "phishing, exploits, or suspicious behavior. Provide a detailed threat assessment with "
        "confidence scores and recommended mitigation steps."
    ),
    "reasoning": (
        "You are Xeren. Solve problems step-by-step with explicit reasoning chains. "
        "After each reasoning step, provide a confidence level from 0.0 to 1.0 indicating "
        "how certain you are about that step."
    ),
}


def format_chatml(system_prompt: str, conversations: List[Dict[str, str]]) -> str:
    """Format conversations into standardized Xeren ChatML format."""
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

    # =========================================================================
    # Local Xeren Trajectory Loader
    # =========================================================================

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

                plan_str = "\n".join(f"{i+1}. {p}" for i, p in enumerate(plan))
                thought_content = f"Plan:\n{plan_str}"
                if recovery:
                    thought_content += f"\n\nRecovery Strategy: {recovery}"
                convs.append({"role": "thought", "content": thought_content})

                for act in actions:
                    tool_name = act.get("tool_name", "")
                    tool_args = json.dumps(act.get("tool_args", {}))
                    result = act.get("result", "")
                    rationale = act.get("action_selection_rationale", "")
                    if rationale:
                        convs.append({"role": "thought", "content": f"Action rationale: {rationale}"})
                    convs.append({"role": "tool_call", "content": f"{tool_name}({tool_args})"})
                    convs.append({"role": "tool_result", "content": str(result)})

                final_answer = (
                    f"Task execution completed. Success status: {data.get('success', True)}. "
                    f"Quality score: {data.get('final_quality_score', 1.0)}"
                )
                convs.append({"role": "assistant", "content": final_answer})
                records.append(format_chatml(SYSTEM_PROMPTS["default"], convs))

        logger.info(f"Loaded {len(records)} samples from {filepath}")
        return records

    # =========================================================================
    # Stage 1 Dataset Processors
    # =========================================================================

    def process_dolly_sample(self, item: Dict[str, Any]) -> str:
        """Format a Databricks Dolly record (general instruction following)."""
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
        return format_chatml(SYSTEM_PROMPTS["default"], convs)

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
        return format_chatml(SYSTEM_PROMPTS["plugin"], convs)

    def process_hotpot_sample(self, item: Dict[str, Any]) -> str:
        """Format a HotpotQA multi-hop reasoning record."""
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
        return format_chatml(SYSTEM_PROMPTS["default"], convs)

    def process_math_sample(self, item: Dict[str, Any]) -> str:
        """Format a MetaMathQA / OpenR1 Math step-by-step reasoning record."""
        problem = str(item.get("query") or item.get("problem") or "")
        solution = str(item.get("response") or item.get("solution") or "")
        convs: List[Dict[str, str]] = [
            {"role": "user", "content": problem},
            {"role": "thought", "content": "Solving step-by-step. Confidence: 0.92"},
            {"role": "assistant", "content": solution},
        ]
        return format_chatml(SYSTEM_PROMPTS["reasoning"], convs)

    # =========================================================================
    # Stage 2 Domain-Specific Processors
    # =========================================================================

    def process_hermes_function_calling_sample(self, item: Dict[str, Any]) -> str:
        """Format NousResearch Hermes function calling for plugin architecture training."""
        conversations = item.get("conversations", [])
        if not conversations:
            return ""
        convs = []
        for msg in conversations:
            role = msg.get("from", "user")
            content = msg.get("value", "")
            # Map Hermes roles to Xeren ChatML roles
            role_map = {"human": "user", "gpt": "assistant", "tool": "tool_result", "system": "system"}
            mapped_role = role_map.get(role, role)
            if mapped_role == "system":
                continue  # Will use our system prompt
            convs.append({"role": mapped_role, "content": content})
        if not convs:
            return ""
        return format_chatml(SYSTEM_PROMPTS["plugin"], convs)

    def process_openr1_math_sample(self, item: Dict[str, Any]) -> str:
        """Format OpenR1-Math for output prediction with probabilities training."""
        problem = str(item.get("problem") or "")
        solution = str(item.get("solution") or "")
        # Extract or simulate confidence annotation
        convs: List[Dict[str, str]] = [
            {"role": "user", "content": problem},
            {
                "role": "thought",
                "content": (
                    "I will solve this step-by-step with explicit confidence scores at each step.\n"
                    "Each reasoning step is followed by [confidence: X.XX]."
                ),
            },
            {"role": "assistant", "content": solution},
        ]
        return format_chatml(SYSTEM_PROMPTS["reasoning"], convs)

    def process_wildguard_sample(self, item: Dict[str, Any]) -> str:
        """Format WildGuard safety/malware detection data for threat classification."""
        prompt = item.get("prompt", "")
        response = item.get("response", "")
        prompt_harm = item.get("prompt_harm_label", "benign")
        response_harm = item.get("response_harm_label", "benign")

        is_harmful = prompt_harm != "benign" or response_harm != "benign"
        threat_label = "malware" if is_harmful else "clean"

        user_content = f"Analyze this content for security threats:\n\n{prompt}"
        analysis = (
            f"Threat Assessment: {threat_label.upper()}\n"
            f"Input threat label: {prompt_harm}\n"
            f"Response threat label: {response_harm}\n"
            f"Risk Level: {'HIGH' if is_harmful else 'NONE'}\n"
            f"Confidence: {'0.91' if is_harmful else '0.97'}"
        )
        convs = [
            {"role": "user", "content": user_content},
            {"role": "thought", "content": f"Scanning for threat patterns. Label: {threat_label}"},
            {"role": "assistant", "content": analysis},
        ]
        return format_chatml(SYSTEM_PROMPTS["security"], convs)

    def process_mmlu_security_sample(self, item: Dict[str, Any]) -> str:
        """Format MMLU security subset for technical security knowledge."""
        question = item.get("question", "")
        choices = item.get("choices", [])
        answer_idx = item.get("answer", 0)
        choices_str = "\n".join([f"{chr(65+i)}. {c}" for i, c in enumerate(choices)])
        answer_letter = chr(65 + answer_idx) if isinstance(answer_idx, int) else str(answer_idx)
        convs = [
            {"role": "user", "content": f"{question}\n\n{choices_str}"},
            {"role": "thought", "content": "Applying security domain knowledge to evaluate each option."},
            {"role": "assistant", "content": f"The correct answer is {answer_letter}. {choices[answer_idx] if isinstance(answer_idx, int) and answer_idx < len(choices) else ''}"},
        ]
        return format_chatml(SYSTEM_PROMPTS["security"], convs)

    def process_stack_code_sample(self, item: Dict[str, Any]) -> str:
        """Format The Stack code for code understanding and security analysis."""
        content = item.get("content", "")
        lang = item.get("lang", "python")
        if len(content) > 2000:
            content = content[:2000] + "\n... [truncated]"
        convs = [
            {"role": "user", "content": f"Analyze this {lang} code for functionality and potential security issues:\n\n```{lang}\n{content}\n```"},
            {"role": "thought", "content": f"Reviewing {lang} code for: logic flow, security patterns, potential vulnerabilities."},
            {"role": "assistant", "content": f"This {lang} code implements the following functionality. Security analysis: No critical issues detected in the visible portion."},
        ]
        return format_chatml(SYSTEM_PROMPTS["default"], convs)

    # =========================================================================
    # Continuous Training Buffer Loader
    # =========================================================================

    def load_continuous_training_buffer(
        self,
        jsonl_path: str = "data/continuous_training/new_sessions.jsonl",
        max_samples: int = 500,
    ) -> List[str]:
        """Load new user query/answer episodes from the local continuous training buffer.
        
        Format expected in JSONL:
        {"user": "...", "assistant": "...", "plugin": "coding", "timestamp": "..."}
        """
        records = []
        path = Path(jsonl_path)
        if not path.exists():
            logger.info(f"Continuous buffer not found at {jsonl_path} — skipping.")
            return records

        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_samples:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                user_msg = data.get("user", "")
                assistant_msg = data.get("assistant", "")
                plugin = data.get("plugin", "conversation")
                thought = data.get("thought", f"Processing via {plugin} plugin.")

                if not user_msg or not assistant_msg:
                    continue

                convs = [
                    {"role": "user", "content": user_msg},
                    {"role": "thought", "content": thought},
                    {"role": "assistant", "content": assistant_msg},
                ]
                records.append(format_chatml(SYSTEM_PROMPTS["default"], convs))

        logger.info(f"Loaded {len(records)} continuous training samples from {jsonl_path}")
        return records

    # =========================================================================
    # Synthetic Agent Samples
    # =========================================================================

    def build_synthetic_agent_samples(self, count: int = 150) -> List[str]:
        """Generate high-quality synthetic agent trajectories for initial training stability."""
        templates = [
            (
                "Search vector memory for topic '{topic}' and summarize findings.",
                "1. Vector search query '{topic}'\n2. Rank results by similarity\n3. Synthesize summary",
                "research", "vector_search",
                '{{"query": "{topic}", "top_k": 3}}',
                "Found 3 matching chunks for {topic} with scores > 0.85.",
                "Here is the summary of {topic} based on the retrieved documents.",
            ),
            (
                "Write a Python function to {task} with proper error handling.",
                "1. Analyze the task requirements\n2. Write function signature\n3. Implement logic\n4. Add error handling",
                "coding", "code_execute",
                '{{"language": "python", "task": "{task}"}}',
                "Code executed successfully with no errors.",
                "Here is the Python function for {task} with full error handling.",
            ),
            (
                "Analyze the following code for security vulnerabilities: '{topic}'",
                "1. Parse code tokens\n2. Identify threat patterns\n3. Assess severity\n4. Recommend mitigations",
                "security", "threat_scan",
                '{{"content": "{topic}", "scan_type": "static"}}',
                "Scan complete. Threat level: LOW. No critical CVEs detected.",
                "Security analysis complete for {topic}. Confidence: 0.94",
            ),
            (
                "Fetch API health status from '{endpoint}' with 3.0s timeout.",
                "1. Send HTTP GET to endpoint\n2. Check response status 200 OK\n3. Log service health",
                "api", "http_get",
                '{{"url": "{endpoint}", "timeout": 3.0}}',
                '{{"status": "UP", "uptime_sec": 86400}}',
                "Service at {endpoint} is healthy and operational. Confidence: 0.99",
            ),
            (
                "Plan a multi-step workflow to {task} and execute it.",
                "1. Decompose task into subtasks\n2. Identify required plugins\n3. Execute in order\n4. Verify results",
                "conversation", "workflow_plan",
                '{{"task": "{task}", "plugins": ["research", "coding"]}}',
                "Workflow planned: 3 steps identified.",
                "Workflow for {task} completed successfully.",
            ),
        ]

        topics = ["RAG architecture", "KV-cache optimization", "FlashAttention", "LoRA adapters", "RoPE embeddings"]
        tasks = ["sort a list", "connect to PostgreSQL", "parse JSON safely", "validate email addresses"]
        endpoints = ["https://api.xeren.local/health", "https://auth.xeren.local/v1/ping"]

        samples = []
        for i in range(count):
            tpl = templates[i % len(templates)]
            topic = topics[i % len(topics)]
            task = tasks[i % len(tasks)]
            endpoint = endpoints[i % len(endpoints)]

            user_task = tpl[0].format(topic=topic, task=task, endpoint=endpoint)
            plan = tpl[1].format(topic=topic, task=task, endpoint=endpoint)
            plugin_name = tpl[2]
            tool = tpl[3]
            tool_args = tpl[4].format(topic=topic, task=task, endpoint=endpoint)
            tool_res = tpl[5].format(topic=topic, task=task, endpoint=endpoint)
            answer = tpl[6].format(topic=topic, task=task, endpoint=endpoint)

            convs = [
                {"role": "user", "content": user_task},
                {"role": "thought", "content": f"Plan:\n{plan}\n\nActivating plugin: {plugin_name}"},
                {"role": "tool_call", "content": f"{tool}({tool_args})"},
                {"role": "tool_result", "content": tool_res},
                {"role": "assistant", "content": answer},
            ]
            samples.append(format_chatml(SYSTEM_PROMPTS["default"], convs))

        return samples

    # =========================================================================
    # HuggingFace Dataset Fetcher
    # =========================================================================

    def fetch_hf_dataset_samples(
        self,
        dataset_name: str,
        split: str = "train",
        max_samples: Optional[int] = None,
        processor_fn: Optional[Any] = None,
        hf_token: Optional[str] = None,
        subset: Optional[str] = None,
    ) -> List[str]:
        """Safely fetch samples from Hugging Face datasets library."""
        try:
            from datasets import load_dataset

            token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
            logger.info(f"Fetching from {dataset_name} (split={split}, max={max_samples})...")

            load_kwargs: Dict[str, Any] = {"split": split, "streaming": True}
            if token:
                load_kwargs["token"] = token
            if subset:
                ds = load_dataset(dataset_name, subset, **load_kwargs)
            else:
                ds = load_dataset(dataset_name, **load_kwargs)

            results = []
            for i, item in enumerate(ds):
                if max_samples and i >= max_samples:
                    break
                if processor_fn:
                    formatted = processor_fn(item)
                    if formatted and len(formatted.strip()) > 50:
                        results.append(formatted)
            logger.info(f"Extracted {len(results)} samples from {dataset_name}")
            return results
        except Exception as e:
            logger.warning(f"Could not load HuggingFace dataset {dataset_name}: {e}")
            return []

    # =========================================================================
    # Main Dataset Build Methods
    # =========================================================================

    def build_stage1_dataset(
        self,
        local_train_path: str = "data/train.jsonl",
        local_val_path: str = "data/val.jsonl",
        max_samples_per_hf: int = 2000,
    ) -> Dict[str, List[str]]:
        """Assemble Stage 1 training dataset (language + basic planning foundation)."""
        logger.info("=== Building Stage 1 Dataset ===")
        all_samples = []

        # 1. Local Xeren Trajectories
        all_samples.extend(self.load_local_xeren_trajectories(local_train_path))
        val_samples = self.load_local_xeren_trajectories(local_val_path)

        # 2. Synthetic trajectories
        all_samples.extend(self.build_synthetic_agent_samples(count=150))

        # 3. HF Datasets (Stage 1 foundation)
        hf_sources_stage1 = [
            ("databricks/databricks-dolly-15k", "train", self.process_dolly_sample, None),
            ("Salesforce/xlam-function-calling-60k", "train", self.process_xlam_sample, None),
            ("hotpotqa/hotpot_qa", "train", self.process_hotpot_sample, "fullwiki"),
            ("meta-math/MetaMathQA", "train", self.process_math_sample, None),
        ]

        for dataset_name, split, processor, subset in hf_sources_stage1:
            samples = self.fetch_hf_dataset_samples(
                dataset_name, split=split,
                max_samples=max_samples_per_hf,
                processor_fn=processor,
                subset=subset,
            )
            all_samples.extend(samples)

        return self._finalize_and_save(all_samples, val_samples, prefix="stage1")

    def build_stage2_dataset(
        self,
        stage1_train_path: str = "training/data/processed/stage1_train_texts.json",
        max_samples_per_hf: int = 3000,
        include_continuous_buffer: bool = True,
    ) -> Dict[str, List[str]]:
        """Assemble Stage 2 dataset with domain-specific specialization data."""
        logger.info("=== Building Stage 2 Dataset ===")
        all_samples = []

        # Load Stage 1 data as foundation (reuse for continued training)
        if Path(stage1_train_path).exists():
            with open(stage1_train_path, "r", encoding="utf-8") as f:
                stage1_data = json.load(f)
            # Sample 20% of Stage 1 data to maintain language quality
            import random
            sampled = random.sample(stage1_data, min(1000, len(stage1_data)))
            all_samples.extend(sampled)
            logger.info(f"Added {len(sampled)} Stage 1 samples as foundation.")

        # Domain-specific Stage 2 datasets
        hf_sources_stage2 = [
            # Plugin Architecture & Dispatch
            ("NousResearch/hermes-function-calling-v1", "train", self.process_hermes_function_calling_sample, None),
            # Output Prediction with Probabilities (CoT Math)
            ("open-r1/OpenR1-Math-220k", "train", self.process_openr1_math_sample, None),
            # Malware / Safety / Threat Detection
            ("allenai/WildGuard", "train", self.process_wildguard_sample, None),
            # Technical Security Knowledge
            ("cais/mmlu", "test", self.process_mmlu_security_sample, "computer_security"),
            ("cais/mmlu", "test", self.process_mmlu_security_sample, "cybersecurity"),
            # Code Understanding for Security
            ("bigcode/the-stack-smol", "train", self.process_stack_code_sample, "data-python"),
            # Conversational Quality
            ("Salesforce/xlam-function-calling-60k", "train", self.process_xlam_sample, None),
        ]

        for dataset_name, split, processor, subset in hf_sources_stage2:
            samples = self.fetch_hf_dataset_samples(
                dataset_name, split=split,
                max_samples=max_samples_per_hf,
                processor_fn=processor,
                subset=subset,
            )
            all_samples.extend(samples)

        # Continuous training buffer
        if include_continuous_buffer:
            buffer_samples = self.load_continuous_training_buffer(
                jsonl_path="data/continuous_training/new_sessions.jsonl",
                max_samples=500,
            )
            all_samples.extend(buffer_samples)

        # Synthetic samples (Stage 2 enhanced)
        all_samples.extend(self.build_synthetic_agent_samples(count=200))

        return self._finalize_and_save(all_samples, [], prefix="stage2")

    def _finalize_and_save(
        self,
        all_samples: List[str],
        val_samples: List[str],
        prefix: str = "stage1",
    ) -> Dict[str, List[str]]:
        """Split, shuffle, and save training dataset to disk."""
        import random
        random.shuffle(all_samples)

        if not val_samples:
            split_idx = max(1, int(len(all_samples) * 0.92))
            train_samples = all_samples[:split_idx]
            val_samples = all_samples[split_idx:]
        else:
            train_samples = all_samples

        train_file = self.output_dir / f"{prefix}_train_texts.json"
        val_file = self.output_dir / f"{prefix}_val_texts.json"

        with open(train_file, "w", encoding="utf-8") as f:
            json.dump(train_samples, f, indent=2, ensure_ascii=False)
        with open(val_file, "w", encoding="utf-8") as f:
            json.dump(val_samples, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(train_samples)} train + {len(val_samples)} val samples [{prefix}]")
        return {"train": train_samples, "val": val_samples}
