"""Intent classification, tool-routing detection, and conversational pattern matching."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from xeren.plugins.conversation.schemas import (
    ConversationIntent,
    ConversationMessage,
    ConversationTone,
    RoutingSignal,
)

# Tool routing keywords and patterns
_TOOL_PATTERNS: List[Tuple[re.Pattern[str], str, str, str]] = [
    # (regex_pattern, suggested_plugin, reason, suggested_action)
    (
        re.compile(r"\b(search the web|search online|web search|look up online|find latest news|google for|google this|find articles on|browse the web for)\b", re.IGNORECASE),
        "research",
        "User requested external web search or information retrieval",
        "web_search",
    ),
    (
        re.compile(r"\b(write a (python|javascript|typescript|c\+\+|rust|bash|sql)?\s*(script|function|code|program|class|module)|generate code|implement an algorithm|debug this code|refactor this code)\b", re.IGNORECASE),
        "coding",
        "User requested code generation, implementation, or refactoring",
        "code_generation",
    ),
    (
        re.compile(r"\b(build a (website|webpage|landing page|portfolio site)|create a (website|webpage|landing page|portfolio site)|generate html/css|design a web page)\b", re.IGNORECASE),
        "website",
        "User requested website generation or UI page creation",
        "website_generation",
    ),
    (
        re.compile(r"\b(analyze this (dataset|csv|data|dataframe)|plot a (chart|graph|histogram)|inspect the dataset|clean this (data|csv)|data visualization)\b", re.IGNORECASE),
        "data",
        "User requested data inspection, analysis, or visualization",
        "data_analysis",
    ),
    (
        re.compile(r"\b(read (the|a)?\s*file|write to (the|a)?\s*file|save this to file|delete (the|a)?\s*file|create a directory|list files in|make a folder)\b", re.IGNORECASE),
        "file",
        "User requested file system read/write or management operations",
        "file_operation",
    ),
    (
        re.compile(r"\b(run (the|an)?\s*automation|schedule (a|the)?\s*task|trigger (the|a)?\s*workflow|execute (the|a)?\s*pipeline)\b", re.IGNORECASE),
        "automation",
        "User requested workflow automation or scheduled task execution",
        "task_execute",
    ),
]

# Greetings
_GREETING_PATTERNS = re.compile(
    r"^(hello|hi|hey|howdy|greetings|salutations|good (morning|afternoon|evening|day)|yo|sup|hiya)(\s+xeren)?[!.,?]?$",
    re.IGNORECASE,
)
_GREETING_CONTAINS = re.compile(
    r"\b(hello|hi|hey|howdy|greetings|good morning|good afternoon|good evening)\b",
    re.IGNORECASE,
)

# Thanks
_THANKS_PATTERNS = re.compile(
    r"\b(thank you|thanks|thx|appreciate it|much appreciated|many thanks|thank you so much|thanks a lot)\b",
    re.IGNORECASE,
)

# Goodbye
_GOODBYE_PATTERNS = re.compile(
    r"\b(bye|goodbye|see you|see ya|have a good day|have a great day|farewell|take care|good night|catch you later)\b",
    re.IGNORECASE,
)

# Clarification
_CLARIFICATION_PATTERNS = re.compile(
    r"\b(what do you mean|can you clarify|could you clarify|please clarify|i don't understand|what does that mean|clarify that|explain what you mean)\b",
    re.IGNORECASE,
)

# Follow-up indicators
_FOLLOW_UP_PATTERNS = re.compile(
    r"\b(tell me more about that|what about the second (one|point)|why is that|what did you mean by that|continue from before|elaborate on that|and then\?|what were we talking about|can you expand on that)\b",
    re.IGNORECASE,
)

# Casual questions
_CASUAL_PATTERNS = re.compile(
    r"\b(how are you|how are you doing|how is it going|how's it going|how's your day|who are you|what are you|what is your name|what's your name|tell me about yourself|what can you do)\b",
    re.IGNORECASE,
)

# Explanation questions
_EXPLANATION_PATTERNS = re.compile(
    r"\b(what is (a|an|the)?|how does .* work|explain (what|how|the)?|why is (a|an|the)?|what does .* stand for|define (a|an|the)?)\b",
    re.IGNORECASE,
)


def detect_routing(message: str) -> Optional[RoutingSignal]:
    """Inspect user message to detect whether external tool or plugin execution is required."""
    clean = message.strip()
    for pattern, plugin_name, reason, action in _TOOL_PATTERNS:
        if pattern.search(clean):
            return RoutingSignal(
                requires_tool=True,
                suggested_plugin=plugin_name,
                reason=reason,
                suggested_action=action,
            )
    return None


def classify_intent(
    message: str,
    context: Optional[List[ConversationMessage]] = None,
) -> ConversationIntent:
    """Classify user communicative intent with priority-based evaluation."""
    clean = message.strip().lower()

    if not clean or clean in {"?", "??", "...", "huh", "what?"}:
        return ConversationIntent.CLARIFICATION

    # 1. Tool execution check takes priority if explicit action is requested
    routing = detect_routing(message)
    if routing and routing.requires_tool:
        return ConversationIntent.TOOL_REQUIRED

    # 2. Clarification request
    if _CLARIFICATION_PATTERNS.search(clean):
        return ConversationIntent.CLARIFICATION

    # 3. Follow-up detection (especially when conversational context exists)
    if _FOLLOW_UP_PATTERNS.search(clean):
        return ConversationIntent.FOLLOW_UP

    # 4. Gratitude / Thanks
    if _THANKS_PATTERNS.search(clean):
        return ConversationIntent.THANKS

    # 5. Parting / Goodbye
    if _GOODBYE_PATTERNS.search(clean):
        return ConversationIntent.GOODBYE

    # 6. Greeting
    if _GREETING_PATTERNS.match(clean) or (_GREETING_CONTAINS.search(clean) and len(clean.split()) <= 4):
        return ConversationIntent.GREETING

    # 7. Casual chit-chat
    if _CASUAL_PATTERNS.search(clean):
        return ConversationIntent.CASUAL

    # 8. Explanation request
    if _EXPLANATION_PATTERNS.search(clean):
        return ConversationIntent.EXPLANATION

    # 9. Contextual follow-up check: if user prompt is very short and context exists
    if context and len(clean.split()) <= 6 and ("why" in clean or "how" in clean or "more" in clean or "and" in clean):
        return ConversationIntent.FOLLOW_UP

    # 10. Default fallback to casual or clarification
    if "?" in clean:
        return ConversationIntent.EXPLANATION

    return ConversationIntent.CASUAL


def extract_antecedent_from_context(context: List[ConversationMessage]) -> Optional[str]:
    """Find the most recent relevant conversational topic from the assistant's previous responses."""
    if not context:
        return None
    # Scan backward for the most recent assistant message
    for msg in reversed(context):
        if msg.role.lower() == "assistant" and msg.content.strip():
            # Return first sentence or brief topic summary
            sentences = [s.strip() for s in msg.content.split(".") if s.strip()]
            if sentences:
                return sentences[0]
            return msg.content[:100].strip()
    return None


__all__ = [
    "detect_routing",
    "classify_intent",
    "extract_antecedent_from_context",
]
