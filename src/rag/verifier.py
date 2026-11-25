"""Policy Gate Evidence Verification Schema and Parser.

Defines the strict Pydantic schema used by the Policy Gate to validate retrieved evidence
before passing context to generation models or agent workflows.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


VerdictType = Literal["PASS", "REJECT_AND_RETRY", "ABSTAIN"]


class EvidenceVerification(BaseModel):
    """Strict Pydantic schema for the RAG Policy Gate verification verdict."""

    model_config = ConfigDict(
        strict=True,
        frozen=False,
        extra="forbid",
        str_strip_whitespace=True,
    )

    IS_RELEVANT: bool = Field(
        ...,
        description="Whether the retrieved evidence is directly relevant to the user query/goal.",
    )
    IS_SUPPORTED: bool = Field(
        ...,
        description="Whether the answer or plan can be factually supported by this evidence without hallucination.",
    )
    HAS_PERMISSION: bool = Field(
        ...,
        description="Whether the current actor identity has read access to the resource.",
    )
    VERDICT: VerdictType = Field(
        ...,
        description="Enforcement decision: PASS (proceed), REJECT_AND_RETRY (reformulate query), or ABSTAIN (decline).",
    )
    correction_hint: str = Field(
        default="",
        description="Actionable suggestion or query reformulation guidance when verdict is not PASS.",
    )

    @field_validator("VERDICT")
    @classmethod
    def validate_verdict_values(cls, value: str) -> str:
        allowed = {"PASS", "REJECT_AND_RETRY", "ABSTAIN"}
        cleaned = value.strip().upper()
        if cleaned not in allowed:
            raise ValueError(f"VERDICT must be one of {allowed}, got '{value}'")
        return cleaned


def parse_evidence_verification(raw_input: Union[str, Dict[str, Any]]) -> EvidenceVerification:
    """Parses JSON or dictionary input into the EvidenceVerification schema.

    Supports raw JSON strings, markdown fenced JSON blocks (```json ... ```),
    and standard Python dictionaries.

    Args:
        raw_input: JSON string or dictionary representing the verification output.

    Returns:
        Validated EvidenceVerification model instance.

    Raises:
        ValueError: If input cannot be parsed as JSON or dictionary.
        pydantic.ValidationError: If validation against schema rules fails.
    """
    if isinstance(raw_input, dict):
        return EvidenceVerification.model_validate(raw_input)

    if not isinstance(raw_input, str):
        raise ValueError(f"Expected str or dict, received: {type(raw_input).__name__}")

    text = raw_input.strip()

    # Extract JSON from markdown fence if present
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        text = code_block_match.group(1).strip()

    try:
        parsed_dict = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse verification response as JSON: {exc}\nRaw content:\n{raw_input}") from exc

    if not isinstance(parsed_dict, dict):
        raise ValueError(f"Decoded JSON must be an object/dict, got: {type(parsed_dict).__name__}")

    return EvidenceVerification.model_validate(parsed_dict)
