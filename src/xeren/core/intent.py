"""IntentClassifier — Automatically detects user intent and maps to the appropriate plugin."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.core.intent")


@dataclass
class IntentResult:
    """Classified user intent with target plugin and confidence."""
    plugin: str
    action: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class IntentClassifier:
    """
    Intelligent Intent Classifier.
    Eliminates the need for users to mention plugin names.

    Automatically routes:
    - 'handle my fiverr account / take upwork order' -> automation / freelance
    - 'create a landing page for bakery / build portfolio website' -> website
    - 'write a python function to parse json / fix bug in test' -> coding
    - 'deep search about quantum computing / research facts' -> research
    - 'clean this csv dataset / visualize sales distribution' -> data
    - 'open my photo in downloads / save file' -> file
    - 'check if this claim is factually true' -> verification
    - 'what did we talk about yesterday / how do you remember' -> experience
    - 'hello / how are you / explain general topic' -> conversation
    """

    # Keyword and pattern rules for fast, zero-latency local classification
    INTENT_RULES = [
        # Multi-Platform Freelance & Workspaces
        (
            re.compile(r"\b(fiverr|upwork|freelancer|linkedin|gig|client order|buyer request|proposal|bid on|freelance)\b", re.I),
            "automation",
            "freelance_platform",
            0.95,
        ),
        # Website building
        (
            re.compile(r"\b(build (a )?website|create (a )?landing page|web page|portfolio site|html css|frontend template)\b", re.I),
            "website",
            "generate_website",
            0.92,
        ),
        # Coding & Development
        (
            re.compile(r"\b(write (a )?code|python script|debug|fix bug|refactor|function|compile|syntax error|git commit|unit test)\b", re.I),
            "coding",
            "write_code",
            0.90,
        ),
        # Deep Research & Knowledge
        (
            re.compile(r"\b(deep search|research|investigate|credibility|sources for|find literature|cross[- ]verify|strawberry)\b", re.I),
            "research",
            "deep_research",
            0.93,
        ),
        # Data Analysis & Cleaning
        (
            re.compile(r"\b(data analysis|csv|dataframe|dataset|pandas|clean data|visualize|histogram|scatter plot|correlation)\b", re.I),
            "data",
            "analyze_data",
            0.91,
        ),
        # File & Document operations
        (
            re.compile(r"\b(open file|read file|save file|read directory|find file|scan folder|photo|document|pdf)\b", re.I),
            "file",
            "file_operation",
            0.88,
        ),
        # Verification & Fact-checking
        (
            re.compile(r"\b(verify claim|fact[- ]check|is it true that|validate evidence|verify this statement)\b", re.I),
            "verification",
            "verify_claim",
            0.92,
        ),
        # Experience & Learning Loop
        (
            re.compile(r"\b(remember this|what did i say earlier|our previous session|learn from this|recall)\b", re.I),
            "experience",
            "retrieve_experience",
            0.89,
        ),
    ]

    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """
        Classify user message into target plugin and intended action.
        """
        cleaned = query.strip()
        if not cleaned:
            return IntentResult(
                plugin="conversation",
                action="chat",
                confidence=1.0,
                reasoning="Empty query defaulted to conversation.",
            )

        # 1. Rule-based pattern matching (ultra-fast, deterministic)
        for pattern, plugin, action, conf in self.INTENT_RULES:
            match = pattern.search(cleaned)
            if match:
                entities = {"matched_term": match.group(0)}
                # Extract platform entity if present
                if plugin == "automation":
                    platform_match = re.search(r"\b(fiverr|upwork|freelancer|linkedin)\b", cleaned, re.I)
                    if platform_match:
                        entities["platform"] = platform_match.group(1).lower()

                return IntentResult(
                    plugin=plugin,
                    action=action,
                    confidence=conf,
                    entities=entities,
                    reasoning=f"Matched pattern '{pattern.pattern}'",
                )

        # 2. Context-aware fallback
        if context and "active_plugin" in context:
            return IntentResult(
                plugin=context["active_plugin"],
                action="continue",
                confidence=0.75,
                reasoning="Retained active contextual plugin.",
            )

        # 3. Default fallback to conversational coaching
        return IntentResult(
            plugin="conversation",
            action="chat",
            confidence=0.70,
            reasoning="Defaulted to conversational intelligence.",
        )


__all__ = ["IntentClassifier", "IntentResult"]
