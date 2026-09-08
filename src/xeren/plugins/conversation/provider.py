"""Conversation providers: abstract interface, deterministic rule engine, and LLM provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional

from xeren.models.base import BaseLLM
from xeren.models.types import ChatMessage, Role
from xeren.plugins.conversation.detector import (
    classify_intent,
    detect_routing,
    extract_antecedent_from_context,
)
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationMessage,
    ConversationResult,
    ConversationTone,
    RoutingSignal,
)

logger = logging.getLogger("xeren.plugins.conversation.provider")

# Built-in educational explanations for standard topics
_EXPLANATION_TOPICS: Dict[str, str] = {
    "api": "An Application Programming Interface (API) is a formal set of protocols and definitions that allows different software applications to communicate and exchange data securely.",
    "neural network": "A neural network is a machine learning model inspired by the human brain's interconnected neurons, consisting of layered nodes that learn complex representations from training data.",
    "recursion": "Recursion is a programming technique where a function solves a computational problem by calling itself with smaller sub-problems until reaching a defined base case.",
    "machine learning": "Machine learning is a subset of artificial intelligence focused on training algorithms to identify patterns in data and make predictions or decisions without explicit rule programming.",
    "python": "Python is a high-level, interpreted, general-purpose programming language renowned for its clear syntax, dynamic typing, and comprehensive ecosystem for data science and web systems.",
    "http": "HTTP (HyperText Transfer Protocol) is the foundational application-layer protocol for distributed hypermedia systems, governing request-response communication between web clients and servers.",
    "xeren": "Xeren is an autonomous AI agent system engineered for high-reliability research, coding, data analysis, and multi-modal task execution with verification gates and learning loops.",
}


class ConversationProvider(ABC):
    """Abstract interface for conversational response generation engines."""

    @abstractmethod
    def generate_response(self, input_data: ConversationInput) -> ConversationResult:
        """Synchronously produce a conversational response conforming to ConversationResult."""
        pass

    async def agenerate_response(self, input_data: ConversationInput) -> ConversationResult:
        """Asynchronously produce a conversational response."""
        return await asyncio.to_thread(self.generate_response, input_data)


class DeterministicConversationProvider(ConversationProvider):
    """Deterministic, rule-based conversation provider.

    Designed for offline operation, unit testing, and instant predictable responses
    without relying on external model weight services or network calls.
    """

    def __init__(
        self,
        canned_responses: Optional[Dict[str, str]] = None,
        error_to_raise: Optional[Exception] = None,
        latency_seconds: float = 0.0,
    ) -> None:
        self._canned_responses: Dict[str, str] = {k.lower(): v for k, v in (canned_responses or {}).items()}
        self.error_to_raise = error_to_raise
        self.latency_seconds = latency_seconds
        self.call_count: int = 0

    def set_canned_response(self, trigger_phrase: str, response: str) -> None:
        """Configure a canned response for a specific user prompt."""
        self._canned_responses[trigger_phrase.strip().lower()] = response

    def generate_response(self, input_data: ConversationInput) -> ConversationResult:
        """Generate a deterministic response adhering to conversational requirements."""
        self.call_count += 1
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)

        if self.error_to_raise is not None:
            raise self.error_to_raise

        user_msg = input_data.message.strip()
        user_msg_lower = user_msg.lower()

        # Check explicit canned overrides first
        for trigger, canned_text in self._canned_responses.items():
            if trigger in user_msg_lower:
                return ConversationResult(
                    response=canned_text,
                    intent=ConversationIntent.CASUAL,
                    tone_used=input_data.tone,
                    context_preserved=bool(input_data.context),
                    metadata={"source": "canned_response"},
                )

        # 1. Detect Intent and Tool Routing
        intent = classify_intent(user_msg, input_data.context)
        routing = detect_routing(user_msg) or RoutingSignal()

        # 2. Construct response based on classified intent and requested tone
        if intent == ConversationIntent.TOOL_REQUIRED and routing.requires_tool:
            response_text = self._build_tool_routing_response(routing, input_data.tone)
            suggested = [f"Proceed with {routing.suggested_plugin}", "Tell me more about what you will do", "Cancel request"]
            return ConversationResult(
                response=response_text,
                intent=intent,
                routing=routing,
                tone_used=input_data.tone,
                context_preserved=False,
                clarification_needed=False,
                suggested_follow_ups=suggested,
                metadata={"source": "tool_routing_detector"},
            )

        if intent == ConversationIntent.GREETING:
            response_text = self._build_greeting_response(input_data.user_name, input_data.tone)
            suggested = ["What can you help me with?", "Tell me about yourself", "Explain how you work"]
            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                suggested_follow_ups=suggested,
                metadata={"source": "greeting_generator"},
            )

        if intent == ConversationIntent.THANKS:
            response_text = self._build_thanks_response(input_data.tone)
            suggested = ["Can you help with something else?", "Have a good day"]
            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                suggested_follow_ups=suggested,
                metadata={"source": "thanks_generator"},
            )

        if intent == ConversationIntent.GOODBYE:
            response_text = self._build_goodbye_response(input_data.tone)
            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                metadata={"source": "goodbye_generator"},
            )

        if intent == ConversationIntent.CASUAL:
            response_text = self._build_casual_response(input_data.tone)
            suggested = ["What capabilities do you have?", "Can you explain an AI concept?"]
            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                suggested_follow_ups=suggested,
                metadata={"source": "casual_generator"},
            )

        if intent == ConversationIntent.EXPLANATION:
            response_text = self._build_explanation_response(user_msg, input_data.tone)
            suggested = ["Can you give an example?", "Tell me more about that", "How does this apply in practice?"]
            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                suggested_follow_ups=suggested,
                metadata={"source": "explanation_generator"},
            )

        if intent == ConversationIntent.FOLLOW_UP:
            antecedent = extract_antecedent_from_context(input_data.context)
            if antecedent:
                response_text = self._build_followup_response(antecedent, user_msg, input_data.tone)
                context_preserved = True
                clarification_needed = False
                suggested = ["Can you explain further?", "What is another aspect?"]
            else:
                response_text = "I would be glad to expand on that! Could you clarify which topic or detail from our conversation you'd like to delve deeper into?"
                context_preserved = False
                clarification_needed = True
                suggested = ["Clarify topic", "Start a new question"]

            return ConversationResult(
                response=response_text,
                intent=intent,
                tone_used=input_data.tone,
                context_preserved=context_preserved,
                clarification_needed=clarification_needed,
                suggested_follow_ups=suggested,
                metadata={"source": "followup_generator", "antecedent": antecedent},
            )

        # Fallback clarification
        response_text = "Could you please provide a bit more detail on what you would like to explore or accomplish? That will help me give you the best assistance."
        return ConversationResult(
            response=response_text,
            intent=ConversationIntent.CLARIFICATION,
            tone_used=input_data.tone,
            clarification_needed=True,
            suggested_follow_ups=["Ask a question", "Request an explanation", "Ask for assistance"],
            metadata={"source": "clarification_fallback"},
        )

    async def agenerate_response(self, input_data: ConversationInput) -> ConversationResult:
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)
        if self.error_to_raise is not None:
            raise self.error_to_raise
        return self.generate_response(input_data)

    def _build_greeting_response(self, user_name: Optional[str], tone: ConversationTone) -> str:
        name_prefix = f", {user_name}" if user_name else ""
        if tone == ConversationTone.PROFESSIONAL:
            return f"Good day{name_prefix}. How may I be of assistance to you today?"
        if tone == ConversationTone.CONCISE:
            return f"Hello{name_prefix}. How can I help you today?"
        if tone == ConversationTone.RESPECTFUL:
            return f"Greetings{name_prefix}. It is a pleasure to connect with you. Please let me know how I may assist."
        if tone == ConversationTone.INFORMATIVE:
            return f"Hello{name_prefix}! I am Xeren, your autonomous assistant for research, development, data analysis, and reasoning. How can we proceed?"
        # Friendly (default)
        return f"Hello{name_prefix}! Great to connect with you. How can I help you today?"

    def _build_casual_response(self, tone: ConversationTone) -> str:
        if tone == ConversationTone.PROFESSIONAL:
            return "I am operating normally and ready to assist you with any research, analytical, or technical inquiries."
        if tone == ConversationTone.CONCISE:
            return "I'm doing well, thank you. Ready to help whenever you are."
        if tone == ConversationTone.RESPECTFUL:
            return "I am functioning smoothly and pleased to be of service. How may I support your work today?"
        # Friendly
        return "I'm doing well, thank you for asking! I'm here and ready to help you with research, coding, analysis, or any questions on your mind."

    def _build_thanks_response(self, tone: ConversationTone) -> str:
        if tone == ConversationTone.PROFESSIONAL:
            return "You are very welcome. Please let me know if any further assistance is required."
        if tone == ConversationTone.CONCISE:
            return "You're welcome! Happy to help."
        if tone == ConversationTone.RESPECTFUL:
            return "It is my genuine pleasure to assist you. Never hesitate to reach out if you need anything else."
        # Friendly
        return "You're very welcome! I'm glad I could help. Let me know if there's anything else you'd like to work on!"

    def _build_goodbye_response(self, tone: ConversationTone) -> str:
        if tone == ConversationTone.PROFESSIONAL:
            return "Goodbye. Have a productive day, and feel free to return whenever you require support."
        if tone == ConversationTone.CONCISE:
            return "Goodbye! Have a great day."
        if tone == ConversationTone.RESPECTFUL:
            return "Farewell. I wish you all the best and remain at your service whenever needed."
        # Friendly
        return "Goodbye! Have a wonderful day, and feel free to reach out anytime you need assistance!"

    def _build_explanation_response(self, message: str, tone: ConversationTone) -> str:
        msg_lower = message.lower()
        matched_text = None
        for key, explanation in _EXPLANATION_TOPICS.items():
            if key in msg_lower:
                matched_text = explanation
                break

        if not matched_text:
            matched_text = f"In general terms, {message.strip().rstrip('?')} refers to a fundamental concept where principles and structured methods are applied to achieve consistent, reliable results."

        if tone == ConversationTone.CONCISE:
            return matched_text
        if tone == ConversationTone.PROFESSIONAL:
            return f"Regarding your inquiry: {matched_text} Please specify if you require an in-depth technical analysis."
        if tone == ConversationTone.INFORMATIVE:
            return f"Here is an overview: {matched_text} It plays a central role in modern computing and software systems."
        # Friendly
        return f"Great question! {matched_text} Would you like an example or deeper exploration of this topic?"

    def _build_followup_response(self, antecedent: str, user_msg: str, tone: ConversationTone) -> str:
        if tone == ConversationTone.CONCISE:
            return f"Building on {antecedent}: this mechanism ensures modularity and consistent outcomes across operations."
        if tone == ConversationTone.PROFESSIONAL:
            return f"Expanding upon our previous discussion regarding '{antecedent}': further analysis indicates this provides substantial reliability and precision in practice."
        # Friendly
        return f"Continuing from our earlier point about '{antecedent}': the key reason behind this is to ensure clarity and maintain flexibility as requirements evolve. Does that address your question?"

    def _build_tool_routing_response(self, routing: RoutingSignal, tone: ConversationTone) -> str:
        plugin = routing.suggested_plugin or "task execution"
        action = routing.suggested_action or "execute the task"
        # Never claim the action was performed! Transparently explain routing.
        if tone == ConversationTone.PROFESSIONAL:
            return f"I note that your request requires active execution ({action}). This falls under the jurisdiction of the '{plugin}' plugin. Would you like me to dispatch this request to the {plugin} tool?"
        if tone == ConversationTone.CONCISE:
            return f"This request requires the '{plugin}' plugin. Ready to dispatch when confirmed."
        # Friendly
        return f"I'd be glad to help with that! However, performing this action requires the '{plugin}' plugin. Would you like me to route this task to the {plugin} tool to proceed?"


class LLMConversationProvider(ConversationProvider):
    """Model-driven conversation provider wrapping an injected BaseLLM.

    Safely sanitizes chain-of-thought tokens, prevents false execution claims,
    and seamlessly falls back to the deterministic engine if model failure occurs.
    """

    def __init__(
        self,
        llm: BaseLLM,
        fallback_provider: Optional[ConversationProvider] = None,
    ) -> None:
        self.llm = llm
        self.fallback = fallback_provider or DeterministicConversationProvider()

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject or replace active LLM provider."""
        self.llm = llm

    def generate_response(self, input_data: ConversationInput) -> ConversationResult:
        """Generate conversational response using the injected LLM, with fallback safety."""
        # 1. First check if message is a tool execution request: maintain safe routing boundary
        routing = detect_routing(input_data.message)
        if routing and routing.requires_tool:
            # Deterministically handle routing signal so model does not hallucinate false tool actions
            return self.fallback.generate_response(input_data)

        # 2. Build sanitized chat messages for LLM
        messages = self._build_prompt_messages(input_data)

        try:
            llm_response = self.llm.generate(messages)
            raw_text = llm_response.content

            # Sanitize chain of thought tokens
            clean_text = self._sanitize_chain_of_thought(raw_text)

            intent = classify_intent(input_data.message, input_data.context)
            context_preserved = bool(input_data.context)

            return ConversationResult(
                response=clean_text,
                intent=intent,
                routing=RoutingSignal(),
                tone_used=input_data.tone,
                context_preserved=context_preserved,
                clarification_needed=False,
                metadata={"model_id": getattr(self.llm.config, "model_id", "custom_llm")},
            )

        except Exception as err:
            logger.warning("LLM provider failed to generate conversational response: %s. Falling back.", err)
            res = self.fallback.generate_response(input_data)
            res.metadata["fallback_from_error"] = str(err)
            return res

    async def agenerate_response(self, input_data: ConversationInput) -> ConversationResult:
        routing = detect_routing(input_data.message)
        if routing and routing.requires_tool:
            return await self.fallback.agenerate_response(input_data)

        messages = self._build_prompt_messages(input_data)
        try:
            llm_response = await self.llm.agenerate(messages)
            clean_text = self._sanitize_chain_of_thought(llm_response.content)
            intent = classify_intent(input_data.message, input_data.context)
            return ConversationResult(
                response=clean_text,
                intent=intent,
                routing=RoutingSignal(),
                tone_used=input_data.tone,
                context_preserved=bool(input_data.context),
                metadata={"model_id": getattr(self.llm.config, "model_id", "custom_llm")},
            )
        except Exception as err:
            logger.warning("Async LLM provider failed: %s. Falling back.", err)
            res = await self.fallback.agenerate_response(input_data)
            res.metadata["fallback_from_error"] = str(err)
            return res

    def _build_prompt_messages(self, input_data: ConversationInput) -> List[ChatMessage]:
        system_instruction = (
            "You are Xeren, a helpful, respectful, and intelligent conversational AI assistant. "
            f"Please respond with a {input_data.tone.value} tone. "
            "Never expose internal chain-of-thought or reasoning scratchpads. "
            "Never claim an action or tool execution was performed when responding in conversation mode. "
            "Be clear, natural, and helpful."
        )
        msgs: List[ChatMessage] = [ChatMessage.system(system_instruction)]

        # Add recent context turns
        for ctx_turn in (input_data.context or [])[-6:]:
            role = Role.USER if ctx_turn.role.lower() == "user" else Role.ASSISTANT
            msgs.append(ChatMessage(role=role, content=ctx_turn.content))

        # Add current user prompt
        msgs.append(ChatMessage.user(input_data.message))
        return msgs

    @staticmethod
    def _sanitize_chain_of_thought(text: str) -> str:
        """Strip any thinking tags or internal monologue tokens from response."""
        # Strip <thought>...</thought> or <thinking>...</thinking>
        cleaned = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        # Strip leading "Chain of thought:" or similar headers
        cleaned = re.sub(r"^(Chain of thought|Internal reasoning):\s*.*?\n\n", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()


__all__ = [
    "ConversationProvider",
    "DeterministicConversationProvider",
    "LLMConversationProvider",
]
