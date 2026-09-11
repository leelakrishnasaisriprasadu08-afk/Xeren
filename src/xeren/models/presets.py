"""Standalone LLM Model Configuration Presets for Xeren.

Defines 20 isolated model configurations spanning temperatures from 0.0 to 1.0.
These presets are kept cleanly decoupled and unmounted from live execution loops
for future specialization and developmental fine-tuning.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from xeren.models.config import ModelConfig


# 20 standalone model presets spanning 0.00 to 1.00 in increments of 0.05
MODEL_PRESETS: Dict[str, ModelConfig] = {
    "xeren-tempo-00-deterministic": ModelConfig(
        model_id="xeren-tempo-00-deterministic",
        provider="local_openweight",
        temperature=0.00,
        top_p=0.10,
        timeout_seconds=60.0,
        extra_params={
            "description": "Strict logic, mathematical precision, security rule audits",
            "tempo_tier": "deterministic",
            "active": False,
        },
    ),
    "xeren-tempo-05-analytical": ModelConfig(
        model_id="xeren-tempo-05-analytical",
        provider="local_openweight",
        temperature=0.05,
        top_p=0.20,
        timeout_seconds=60.0,
        extra_params={
            "description": "Strict factual retrieval, JSON schemas, SQL generation",
            "tempo_tier": "analytical",
            "active": False,
        },
    ),
    "xeren-tempo-10-code-strict": ModelConfig(
        model_id="xeren-tempo-10-code-strict",
        provider="local_openweight",
        temperature=0.10,
        top_p=0.40,
        timeout_seconds=60.0,
        extra_params={
            "description": "Precise code compilation and syntax error localization",
            "tempo_tier": "code_strict",
            "active": False,
        },
    ),
    "xeren-tempo-15-factual-rag": ModelConfig(
        model_id="xeren-tempo-15-factual-rag",
        provider="local_openweight",
        temperature=0.15,
        top_p=0.60,
        timeout_seconds=60.0,
        extra_params={
            "description": "Citation verification, contract extraction, evidence synthesis",
            "tempo_tier": "factual_rag",
            "active": False,
        },
    ),
    "xeren-tempo-20-balanced-code": ModelConfig(
        model_id="xeren-tempo-20-balanced-code",
        provider="local_openweight",
        temperature=0.20,
        top_p=0.80,
        timeout_seconds=60.0,
        extra_params={
            "description": "Standard code refactoring and algorithmic implementations",
            "tempo_tier": "balanced_code",
            "active": False,
        },
    ),
    "xeren-tempo-25-documentation": ModelConfig(
        model_id="xeren-tempo-25-documentation",
        provider="local_openweight",
        temperature=0.25,
        top_p=0.85,
        timeout_seconds=60.0,
        extra_params={
            "description": "Technical documentation generation and API specifications",
            "tempo_tier": "documentation",
            "active": False,
        },
    ),
    "xeren-tempo-30-structured-plan": ModelConfig(
        model_id="xeren-tempo-30-structured-plan",
        provider="local_openweight",
        temperature=0.30,
        top_p=0.90,
        timeout_seconds=60.0,
        extra_params={
            "description": "Multi-step task decomposition and workflow planning",
            "tempo_tier": "structured_plan",
            "active": False,
        },
    ),
    "xeren-tempo-35-agent-controller": ModelConfig(
        model_id="xeren-tempo-35-agent-controller",
        provider="local_openweight",
        temperature=0.35,
        top_p=0.92,
        timeout_seconds=60.0,
        extra_params={
            "description": "Tool selection, plugin routing, intent triage",
            "tempo_tier": "agent_controller",
            "active": False,
        },
    ),
    "xeren-tempo-40-reasoning": ModelConfig(
        model_id="xeren-tempo-40-reasoning",
        provider="local_openweight",
        temperature=0.40,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Step-by-step cognitive reasoning and chain-of-thought",
            "tempo_tier": "reasoning",
            "active": False,
        },
    ),
    "xeren-tempo-45-assistant-copilot": ModelConfig(
        model_id="xeren-tempo-45-assistant-copilot",
        provider="local_openweight",
        temperature=0.45,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Pair programming assistant and contextual code suggestions",
            "tempo_tier": "assistant_copilot",
            "active": False,
        },
    ),
    "xeren-tempo-50-multiturn-refactor": ModelConfig(
        model_id="xeren-tempo-50-multiturn-refactor",
        provider="local_openweight",
        temperature=0.50,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Multi-turn iterative code refactoring and incremental revisions",
            "tempo_tier": "multiturn_refactor",
            "active": False,
        },
    ),
    "xeren-tempo-55-explainer": ModelConfig(
        model_id="xeren-tempo-55-explainer",
        provider="local_openweight",
        temperature=0.55,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Educational explanations, conceptual analogies, tutorials",
            "tempo_tier": "explainer",
            "active": False,
        },
    ),
    "xeren-tempo-60-summarizer": ModelConfig(
        model_id="xeren-tempo-60-summarizer",
        provider="local_openweight",
        temperature=0.60,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Document synthesis and high-level abstracts",
            "tempo_tier": "summarizer",
            "active": False,
        },
    ),
    "xeren-tempo-65-creative-writer": ModelConfig(
        model_id="xeren-tempo-65-creative-writer",
        provider="local_openweight",
        temperature=0.65,
        top_p=0.95,
        timeout_seconds=60.0,
        extra_params={
            "description": "Engaging copywriting, UI microcopy, and descriptive text",
            "tempo_tier": "creative_writer",
            "active": False,
        },
    ),
    "xeren-tempo-70-ideation": ModelConfig(
        model_id="xeren-tempo-70-ideation",
        provider="local_openweight",
        temperature=0.70,
        top_p=0.98,
        timeout_seconds=60.0,
        extra_params={
            "description": "Architecture brainstorming and system design options",
            "tempo_tier": "ideation",
            "active": False,
        },
    ),
    "xeren-tempo-75-design-stylist": ModelConfig(
        model_id="xeren-tempo-75-design-stylist",
        provider="local_openweight",
        temperature=0.75,
        top_p=0.98,
        timeout_seconds=60.0,
        extra_params={
            "description": "Creative UI/UX styling suggestions, CSS palettes, aesthetics",
            "tempo_tier": "design_stylist",
            "active": False,
        },
    ),
    "xeren-tempo-80-storyteller": ModelConfig(
        model_id="xeren-tempo-80-storyteller",
        provider="local_openweight",
        temperature=0.80,
        top_p=0.98,
        timeout_seconds=60.0,
        extra_params={
            "description": "Narrative generation, user persona simulations",
            "tempo_tier": "storyteller",
            "active": False,
        },
    ),
    "xeren-tempo-85-divergent-search": ModelConfig(
        model_id="xeren-tempo-85-divergent-search",
        provider="local_openweight",
        temperature=0.85,
        top_p=0.99,
        timeout_seconds=60.0,
        extra_params={
            "description": "Lateral problem solving and alternative paradigms",
            "tempo_tier": "divergent_search",
            "active": False,
        },
    ),
    "xeren-tempo-90-brainstormer": ModelConfig(
        model_id="xeren-tempo-90-brainstormer",
        provider="local_openweight",
        temperature=0.90,
        top_p=0.99,
        timeout_seconds=60.0,
        extra_params={
            "description": "Unconstrained exploration and experimental hypothesis generation",
            "tempo_tier": "brainstormer",
            "active": False,
        },
    ),
    "xeren-tempo-100-creative-wildcard": ModelConfig(
        model_id="xeren-tempo-100-creative-wildcard",
        provider="local_openweight",
        temperature=1.00,
        top_p=1.00,
        timeout_seconds=60.0,
        extra_params={
            "description": "Maximum diversity sampling, unconventional ideas, wildcard solutions",
            "tempo_tier": "creative_wildcard",
            "active": False,
        },
    ),
}


def get_model_preset(model_id: str) -> Optional[ModelConfig]:
    """Retrieve a model preset by its identifier."""
    return MODEL_PRESETS.get(model_id)


def list_model_presets() -> List[ModelConfig]:
    """Return all 20 standalone model presets ordered by temperature."""
    return sorted(list(MODEL_PRESETS.values()), key=lambda m: m.temperature)


def get_presets_by_temperature_range(
    min_temp: float = 0.0,
    max_temp: float = 1.0,
) -> List[ModelConfig]:
    """Filter presets within a temperature range [min_temp, max_temp]."""
    return [
        m for m in list_model_presets()
        if min_temp <= m.temperature <= max_temp
    ]
