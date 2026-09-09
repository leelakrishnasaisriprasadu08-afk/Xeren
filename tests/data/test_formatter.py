"""Unit tests for training data formatters (SFT, Structured Agent, DPO)."""

import pytest

from xeren.data.dataset import ExperienceDataset
from xeren.data.formatter import (
    DPOExample,
    ExperienceFormatter,
    SFTChatExample,
    StructuredAgentExample,
)
from xeren.data.schema import (
    ActionStep,
    AlternativeCandidate,
    DatasetSplit,
    ExperienceRecord,
    RetrievalItem,
    VerificationDetails,
)


def _make_sample_record(sample_id: str = "fmt-01") -> ExperienceRecord:
    return ExperienceRecord(
        sample_id=sample_id,
        task="Find config and compute size",
        plan=["Search config", "Compute size"],
        actions=[
            ActionStep(
                step_index=0,
                plan_step="Search config",
                tool_name="search",
                tool_args={"query": "config"},
                action_selection_rationale="Find config file",
                result="Found config.json",
                success=True,
            ),
            ActionStep(
                step_index=1,
                plan_step="Compute size",
                tool_name="calculator",
                tool_args={"expression": "100 + 20"},
                result="120",
                success=True,
            ),
        ],
        prediction_confidence=0.95,
        verification=VerificationDetails(
            verified=True,
            verifier="unit_test",
            score=0.98,
            details={"ok": True},
        ),
        alternatives=[
            AlternativeCandidate(
                candidate_action="manual_inspect",
                score=0.4,
                comparison_note="Manual is slower",
                rejected_reason="Tool automation preferred",
            )
        ],
        retrieval_items=[
            RetrievalItem(
                source_id="cfg#1",
                content="Config parameters for app.",
                is_useful=True,
                relevance_score=0.9,
            ),
            RetrievalItem(
                source_id="noise#1",
                content="Unrelated noise text.",
                is_useful=False,
                relevance_score=0.1,
            ),
        ],
        success=True,
        final_quality_score=0.96,
        split=DatasetSplit.TRAIN,
        is_verified=True,
    )


def test_formatter_to_sft_chat() -> None:
    formatter = ExperienceFormatter()
    rec = _make_sample_record()

    sft_ex = formatter.to_sft_chat(rec)
    assert isinstance(sft_ex, SFTChatExample)
    assert sft_ex.sample_id == "fmt-01"

    # Messages structure: system, user, assistant
    roles = [m.role for m in sft_ex.messages]
    assert roles == ["system", "user", "assistant"]

    # User message contains task and useful context
    user_msg = sft_ex.messages[1].content
    assert "Task: Find config and compute size" in user_msg
    assert "Config parameters for app." in user_msg
    assert "Unrelated noise text." not in user_msg  # Filtered out irrelevant chunk

    # Assistant message contains plan and actions
    asst_msg = sft_ex.messages[2].content
    assert "Plan:" in asst_msg
    assert "1. Search config" in asst_msg
    assert "Action: search" in asst_msg
    assert "Action: calculator" in asst_msg
    assert "Verification: Verified by unit_test" in asst_msg


def test_formatter_to_structured_agent() -> None:
    formatter = ExperienceFormatter()
    rec = _make_sample_record()

    agent_ex = formatter.to_structured_agent(rec)
    assert isinstance(agent_ex, StructuredAgentExample)
    assert agent_ex.task == rec.task
    assert len(agent_ex.trajectory) == 2
    assert agent_ex.verification["verified"] is True

    prompt, target = agent_ex.to_formatted_prompt_and_target()
    assert "<|system|>" in prompt
    assert "<|user|>" in prompt
    assert "<|assistant|>" in prompt
    assert "<|plan|>" in target
    assert "<|action|>" in target
    assert "<|observation|>" in target
    assert "<|verification|>" in target


def test_formatter_to_dpo_pairs() -> None:
    formatter = ExperienceFormatter()
    rec = _make_sample_record()

    pairs = formatter.to_dpo_pairs(rec)
    assert len(pairs) == 1
    dpo = pairs[0]
    assert isinstance(dpo, DPOExample)
    assert dpo.sample_id == "fmt-01-dpo-0"
    assert "Task: Find config and compute size" in dpo.prompt
    assert "Action: search" in dpo.chosen
    assert "Action: manual_inspect" in dpo.rejected
    assert "Tool automation preferred" in dpo.rejected


def test_formatter_dataset_conversions() -> None:
    formatter = ExperienceFormatter()
    rec1 = _make_sample_record("rec-1")
    rec2 = _make_sample_record("rec-2")
    rec2.task = "A distinct second task"

    ds = ExperienceDataset([rec1, rec2])

    sft_list = formatter.format_dataset_for_sft(ds)
    assert len(sft_list) == 2

    struct_list = formatter.format_dataset_for_structured_agent(ds)
    assert len(struct_list) == 2

    dpo_list = formatter.format_dataset_for_dpo(ds)
    assert len(dpo_list) == 2
