"""Dataset formatting and conversion utilities for Xeren model training.

Transforms ExperienceRecord trajectories into formats suitable for:
1. SFT Chat (instruction tuning / ChatML)
2. Structured Agent (Task -> Context -> Plan -> Action -> Observation -> Verification -> Outcome)
3. DPO / Preference Optimization (Chosen vs Rejected pairs from alternatives & corrections)
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from xeren.data.dataset import ExperienceDataset
from xeren.data.schema import ExperienceRecord


DEFAULT_SYSTEM_PROMPT = (
    "You are Xeren, an autonomous AI system designed for rigorous reasoning, planning, "
    "tool execution, and empirical self-verification."
)


class ChatMessage(BaseModel):
    """A single turn in an SFT chat conversation."""
    role: str = Field(..., description="Message role: system, user, assistant, or tool")
    content: str = Field(..., description="Text content of the message")
    name: Optional[str] = Field(default=None, description="Optional tool/participant name")


class SFTChatExample(BaseModel):
    """Supervised fine-tuning conversation example."""
    sample_id: str
    messages: List[ChatMessage]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "messages": [m.model_dump(exclude_none=True) for m in self.messages],
            "metadata": self.metadata,
        }


class StructuredAgentExample(BaseModel):
    """Structured representation preserving the Xeren agent loop for specialized model training."""
    sample_id: str
    task: str
    retrieved_context: Optional[str] = None
    plan: List[str] = Field(default_factory=list)
    trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    verification: Dict[str, Any] = Field(default_factory=dict)
    outcome: str
    final_quality_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_formatted_prompt_and_target(self) -> Tuple[str, str]:
        """Convert into prompt and target strings with structured agent tokens."""
        prompt_parts = [
            f"<|system|>\n{DEFAULT_SYSTEM_PROMPT}\n<|im_end|>",
            f"<|user|>\nTask: {self.task}",
        ]
        if self.retrieved_context:
            prompt_parts.append(f"Context:\n{self.retrieved_context}")
        prompt_parts.append("<|im_end|>\n<|assistant|>")
        prompt = "\n".join(prompt_parts)

        target_parts = []
        if self.plan:
            plan_lines = "\n".join(f"{i+1}. {step}" for i, step in enumerate(self.plan))
            target_parts.append(f"<|plan|>\n{plan_lines}\n<|im_end|>")

        for action in self.trajectory:
            action_line = f"<|action|>\nTool: {action['tool_name']}\nArgs: {json.dumps(action['tool_args'], sort_keys=True)}\n<|im_end|>"
            obs_line = f"<|observation|>\nResult: {action['result']}\n<|im_end|>"
            target_parts.append(action_line)
            target_parts.append(obs_line)

        verif_str = f"<|verification|>\nVerified: {self.verification.get('verified', True)} | Score: {self.verification.get('score', 1.0)}\n<|im_end|>"
        target_parts.append(verif_str)
        target_parts.append(f"Outcome: {self.outcome}\n<|im_end|>")

        target = "\n".join(target_parts)
        return prompt, target


class DPOExample(BaseModel):
    """Direct Preference Optimization (DPO) pairwise training example."""
    sample_id: str
    prompt: str
    chosen: str
    rejected: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "metadata": self.metadata,
        }


class ExperienceFormatter:
    """Formats ExperienceRecord datasets into SFT, Structured Agent, and DPO training representations."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def to_sft_chat(
        self,
        record: ExperienceRecord,
        include_context: bool = True,
    ) -> SFTChatExample:
        """Convert an ExperienceRecord into an SFT multi-turn or single-turn chat conversation."""
        messages: List[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt)
        ]

        # Build user message with optional retrieved context
        user_content = f"Task: {record.task}"
        useful_context = [
            item.content for item in record.retrieval_items if item.is_useful
        ]
        if include_context and useful_context:
            context_block = "\n".join(f"- {c}" for c in useful_context)
            user_content += f"\n\nRelevant Context:\n{context_block}"

        messages.append(ChatMessage(role="user", content=user_content))

        # Build assistant response representing planning, actions, and verified outcome
        assistant_sections: List[str] = []

        if record.plan:
            plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(record.plan))
            assistant_sections.append(f"Plan:\n{plan_text}")

        for step in record.actions:
            step_text = f"Action: {step.tool_name}({json.dumps(step.tool_args, sort_keys=True)})\nResult: {step.result}"
            if step.correction:
                step_text += f"\nCorrection Applied: {step.correction}"
            assistant_sections.append(step_text)

        # Verification and outcome
        if record.success:
            last_result = record.actions[-1].result if record.actions else "Task completed successfully."
            outcome_text = f"Verification: Verified by {record.verification.verifier} (score: {record.verification.score:.2f}).\nConclusion: {last_result}"
        else:
            outcome_text = f"Verification: Task halted. Reason: {record.failure_reason or 'Execution failed'}."

        assistant_sections.append(outcome_text)

        assistant_content = "\n\n".join(assistant_sections)
        messages.append(ChatMessage(role="assistant", content=assistant_content))

        return SFTChatExample(
            sample_id=record.sample_id,
            messages=messages,
            metadata={
                "prediction_confidence": record.prediction_confidence,
                "final_quality_score": record.final_quality_score,
                "verification_score": record.verification.score,
                "split": record.split.value,
                "success": record.success,
            },
        )

    def to_structured_agent(self, record: ExperienceRecord) -> StructuredAgentExample:
        """Convert an ExperienceRecord into a StructuredAgentExample."""
        useful_chunks = [
            item.content for item in record.retrieval_items if item.is_useful
        ]
        context_str = "\n".join(f"- {c}" for c in useful_chunks) if useful_chunks else None

        trajectory = [
            {
                "step_index": a.step_index,
                "plan_step": a.plan_step,
                "tool_name": a.tool_name,
                "tool_args": a.tool_args,
                "result": a.result,
                "success": a.success,
                "correction": a.correction,
            }
            for a in record.actions
        ]

        outcome = record.actions[-1].result if record.actions else ("Success" if record.success else "Failed")

        return StructuredAgentExample(
            sample_id=record.sample_id,
            task=record.task,
            retrieved_context=context_str,
            plan=record.plan,
            trajectory=trajectory,
            verification={
                "verified": record.verification.verified,
                "verifier": record.verification.verifier,
                "score": record.verification.score,
            },
            outcome=outcome,
            final_quality_score=record.final_quality_score,
            metadata={
                "split": record.split.value,
                "success": record.success,
                "prediction_confidence": record.prediction_confidence,
            },
        )

    def to_dpo_pairs(self, record: ExperienceRecord) -> List[DPOExample]:
        """Derive DPO preference pairs from alternatives evaluated during trajectory execution."""
        pairs: List[DPOExample] = []
        if not record.alternatives:
            return pairs

        prompt = f"Task: {record.task}"
        if record.plan:
            prompt += f"\nPlan:\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(record.plan))

        chosen_action = (
            f"Action: {record.actions[0].tool_name}({json.dumps(record.actions[0].tool_args, sort_keys=True)})\n"
            f"Result: {record.actions[0].result}"
            if record.actions
            else "Follow verified plan and execute designated tool."
        )

        for idx, alt in enumerate(record.alternatives):
            rejected_action = (
                f"Action: {alt.candidate_action}\n"
                f"Rejected Reason: {alt.rejected_reason} (Note: {alt.comparison_note})"
            )
            pairs.append(
                DPOExample(
                    sample_id=f"{record.sample_id}-dpo-{idx}",
                    prompt=prompt,
                    chosen=chosen_action,
                    rejected=rejected_action,
                    metadata={
                        "parent_sample_id": record.sample_id,
                        "alternative_score": alt.score,
                        "split": record.split.value,
                    },
                )
            )

        return pairs

    def format_dataset_for_sft(
        self,
        dataset: ExperienceDataset,
        only_eligible: bool = True,
    ) -> List[SFTChatExample]:
        """Format an entire dataset into SFT chat examples."""
        target_ds = dataset.filter_for_training() if only_eligible else dataset
        return [self.to_sft_chat(r) for r in target_ds.records]

    def format_dataset_for_structured_agent(
        self,
        dataset: ExperienceDataset,
        only_eligible: bool = True,
    ) -> List[StructuredAgentExample]:
        """Format an entire dataset into StructuredAgentExample records."""
        target_ds = dataset.filter_for_training() if only_eligible else dataset
        return [self.to_structured_agent(r) for r in target_ds.records]

    def format_dataset_for_dpo(
        self,
        dataset: ExperienceDataset,
    ) -> List[DPOExample]:
        """Extract all DPO preference pairs from dataset alternatives."""
        pairs: List[DPOExample] = []
        for r in dataset.records:
            pairs.extend(self.to_dpo_pairs(r))
        return pairs
