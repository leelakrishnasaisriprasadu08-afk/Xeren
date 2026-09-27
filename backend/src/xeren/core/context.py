"""Core runtime context holding LLM provider and session states."""

from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field

from xeren.models.base import BaseLLM


class CoreContext(BaseModel):
    """Runtime context for Xeren Core orchestrator."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Active session ID")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")
    llm: Optional[BaseLLM] = Field(default=None, description="Core active LLM provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session and environment metadata")

    model_config = {"arbitrary_types_allowed": True}


__all__ = ["CoreContext"]
