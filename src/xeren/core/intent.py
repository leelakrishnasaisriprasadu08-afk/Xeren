"""IntentClassifier — Automatically detects user intent and maps to the appropriate pipeline and plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("xeren.core.intent")


class RoutingCategory(str, Enum):
    """Three-tier high-level intent routing."""
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"  # Routed to LLM
    XEREN_PROJECT = "XEREN_PROJECT"          # Routed to RAG / internal project docs
    ACTION_REQUEST = "ACTION_REQUEST"        # Routed to Agent / Tools execution


@dataclass
class IntentResult:
    """Classified user intent with routing category, target plugin, and confidence."""
    category: RoutingCategory
    plugin: str
    action: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class IntentClassifier:
    """
    Intelligent Intent Classifier & Router.
    Routes queries according to Xeren 3-Tier Architecture:
    1. GENERAL_KNOWLEDGE -> LLM direct response
    2. XEREN_PROJECT -> RAG & Internal Knowledge Base
    3. ACTION_REQUEST -> Agent Controller & Specialized Plugins
    """

    # Rules for Xeren Project specifics (codebase, architecture, checkpoints, training)
    XEREN_PROJECT_PATTERNS = [
        re.compile(r"\b(xeren|xeren's|core architecture|runtime\.py|agentcontroller|qlora|curriculum|experience dataset|hallucination guard|training checkpoint|stage1|stage2)\b", re.I),
        re.compile(r"\b(how (does|do) (xeren|the controller|the agent) work|xeren specs|xeren pipeline|in this repo|in our codebase)\b", re.I),
    ]

    # Rules for Action Requests (tools, automation, file, code execution, deep search)
    ACTION_RULES = [
        # Desktop Apps, OS & Command Execution
        (
            re.compile(r"\b(open|launch|run|execute|start|close|kill|terminate)\s+(chrome|notepad|code|vscode|terminal|powershell|cmd|app|application|command|process)\b|\b(download|curl|wget)\b", re.I),
            "automation",
            "desktop_operator",
            0.95,
        ),
        # Multi-Platform Freelance & Automation
        (
            re.compile(r"\b(fiverr|upwork|freelancer|linkedin|gig|client order|buyer request|proposal|bid on|freelance|automate)\b", re.I),
            "automation",
            "freelance_platform",
            0.95,
        ),
        # Website building, 3D interactive applications & digital objects
        (
            re.compile(
                r"\b((build|create|design|generate|make|develop|render|launch|set\s+up)\s+(a|an|the|some|me\s+a)?\s*(3[- ]?d\s+)?(site[s]?|website[s]?|web\s*page[s]?|web\s*app[s]?|landing\s*page[s]?|portfolio[s]?|showroom[s]?|car\s*showroom[s]?|model[s]?|object[s]?|scene[s]?|asset[s]?|view[s]?|space[s]?|cars?|hypercars?)|3[- ]?d\s+(site[s]?|website[s]?|page[s]?|app[s]?|showroom[s]?|model[s]?|object[s]?|view[s]?|scene[s]?|asset[s]?)|landing\s*page|website|web\s*app|portfolio\s*site|html\s*css|frontend\s*template|three\.?js|webgl)\b",
                re.I,
            ),
            "website",
            "generate_website",
            0.95,
        ),
        # Coding, Development & Sandbox Execution
        (
            re.compile(
                r"\b(write\s+(a\s+)?(python\s+)?(code|script|function|program)|python\s+(script|function|code)|run\s+(python\s+)?(code|script|sandbox)|execute\s+(python\s+)?(code|script)|debug|fix\s+bug|refactor|compile|syntax\s+error|git\s+commit|unit\s+test|implement\s+(a\s+)?(python\s+)?(function|method|class|algorithm))\b",
                re.I,
            ),
            "coding",
            "write_code",
            0.92,
        ),
        # Deep Research, Web Scraping & Open Source Assets
        (
            re.compile(
                r"\b(search\s+(the\s+)?(web|internet|online)|scrape\s+(free\s+)?(open[- ]source\s+)?(resources|assets|data|models|info|web|sites?)|deep\s+search|research|investigate|credibility|sources\s+for|find\s+literature|cross[- ]verify|web\s+search|look\s+up\s+(on\s+)?online|gather\s+resources|find\s+(open[- ]source|free)\s+resources)\b",
                re.I,
            ),
            "research",
            "deep_research",
            0.94,
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
            re.compile(r"\b(write .* to (a )?file|open file|read file|save file|read directory|find file|scan folder|photo|document|pdf|list files)\b", re.I),
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
        Classify user message into routing category, target plugin, and intended action.
        """
        cleaned = query.strip()
        if not cleaned:
            return IntentResult(
                category=RoutingCategory.GENERAL_KNOWLEDGE,
                plugin="conversation",
                action="chat",
                confidence=1.0,
                reasoning="Empty query defaulted to general conversation.",
            )

        # Explicit context force_category override
        if context and "force_category" in context:
            fc = str(context["force_category"]).upper()
            cat = RoutingCategory[fc] if fc in RoutingCategory.__members__ else (
                RoutingCategory.XEREN_PROJECT if "project" in fc.lower() else
                RoutingCategory.ACTION_REQUEST if "action" in fc.lower() else
                RoutingCategory.GENERAL_KNOWLEDGE
            )
            return IntentResult(
                category=cat,
                plugin=context.get("active_plugin", "conversation"),
                action="forced",
                confidence=1.0,
                reasoning="Context force_category override applied.",
            )

        # 1. Check for Xeren Project specifics -> RAG
        for pat in self.XEREN_PROJECT_PATTERNS:
            match = pat.search(cleaned)
            if match:
                return IntentResult(
                    category=RoutingCategory.XEREN_PROJECT,
                    plugin="knowledge",
                    action="project_rag",
                    confidence=0.94,
                    entities={"matched_term": match.group(0)},
                    reasoning=f"Matched project query pattern '{pat.pattern}' -> routed to RAG.",
                )

        # 2. Check for Action Requests -> Specialized Agent/Tools
        for pattern, plugin, action, conf in self.ACTION_RULES:
            match = pattern.search(cleaned)
            if match:
                entities = {"matched_term": match.group(0)}
                if plugin == "automation":
                    platform_match = re.search(r"\b(fiverr|upwork|freelancer|linkedin)\b", cleaned, re.I)
                    if platform_match:
                        entities["platform"] = platform_match.group(1).lower()

                return IntentResult(
                    category=RoutingCategory.ACTION_REQUEST,
                    plugin=plugin,
                    action=action,
                    confidence=conf,
                    entities=entities,
                    reasoning=f"Matched action pattern '{pattern.pattern}' -> routed to Agent/Tools ({plugin}).",
                )

        # 3. Context-aware fallback
        if context and "active_plugin" in context:
            active_p = context["active_plugin"]
            return IntentResult(
                category=RoutingCategory.ACTION_REQUEST if active_p != "conversation" else RoutingCategory.GENERAL_KNOWLEDGE,
                plugin=active_p,
                action="continue",
                confidence=0.75,
                reasoning="Retained active contextual plugin.",
            )

        # 4. Default fallback -> General Knowledge / LLM
        return IntentResult(
            category=RoutingCategory.GENERAL_KNOWLEDGE,
            plugin="conversation",
            action="chat",
            confidence=0.85,
            reasoning="Routed to General Knowledge LLM.",
        )


__all__ = ["IntentClassifier", "IntentResult", "RoutingCategory"]
