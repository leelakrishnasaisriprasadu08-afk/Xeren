"""Schemas for LLM Self-Improvement Engine, Pattern Recognition, and Adaptive Prompt Evolution."""

from __future__ import annotations

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ObservationSource(str, Enum):
    """Source of an observation captured by the learning loop."""
    USER_QUERY = "user_query"
    USER_TASK = "user_task"
    WEB_SEARCH = "web_search"
    BOT_MODEL_OUTPUT = "bot_model_output"
    VERIFICATION_RESULT = "verification_result"


class UserQueryPattern(BaseModel):
    """Pattern identified from repeatedly asked questions, task workflows, or user preferences."""
    pattern_id: str
    category: str  # "architecture" | "coding_style" | "verification" | "research" | "tool_preference"
    intent_cluster: str
    sample_queries: List[str] = Field(default_factory=list)
    frequency_count: int = 1
    confidence: float = 0.85
    first_observed: str
    last_observed: str
    distilled_preference: str
    recommended_adaptation: str
    is_active: bool = True


class SearchModelInsight(BaseModel):
    """Knowledge and consensus patterns distilled from live web search and bot models."""
    insight_id: str
    topic: str
    consensus_facts: List[str] = Field(default_factory=list)
    recurring_domains: List[str] = Field(default_factory=list)
    failure_traps_identified: List[str] = Field(default_factory=list)
    bot_models_evaluated: List[str] = Field(default_factory=list)
    consensus_agreement_pct: float = 95.0
    discovered_at: str


class AdaptiveSystemDirective(BaseModel):
    """Active learned directive evolved by the LLM to improve future reasoning and performance."""
    directive_id: str
    title: str
    category: str  # "code_generation" | "query_routing" | "search_synthesis" | "error_mitigation"
    directive_prompt: str
    source_patterns: List[str] = Field(default_factory=list)
    effectiveness_score: float = 0.92
    is_active: bool = True
    evolution_cycle: int = 1
    created_at: str
    updated_at: str


class SelfImprovementReport(BaseModel):
    """Telemetry report describing the LLM's current self-improvement status."""
    adaptive_score: float = 94.8  # 0.0 to 100.0
    total_observations_recorded: int = 0
    patterns_count: int = 0
    insights_count: int = 0
    active_directives_count: int = 0
    evolution_cycles_completed: int = 1
    recent_improvements: List[str] = Field(default_factory=list)
    timestamp: str


class RecordObservationRequest(BaseModel):
    source: ObservationSource
    content: str
    context: Optional[Dict[str, Any]] = None
    outcome_success: bool = True


class AnalyzeImprovementsRequest(BaseModel):
    min_frequency: int = 2
    force_directive_synthesis: bool = False


class ToggleDirectiveRequest(BaseModel):
    is_active: bool
