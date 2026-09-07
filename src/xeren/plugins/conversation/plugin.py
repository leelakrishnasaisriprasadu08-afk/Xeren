"""Conversation Plugin implementation conforming strictly to the Xeren BasePlugin contract."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging
import time
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel

from xeren.models.base import BaseLLM
from xeren.plugins.contract import (
    BasePlugin,
    HealthCheckResult,
    PluginExecutionContext,
    PluginExecutionResult,
    PluginHealthStatus,
    PluginManifest,
)
from xeren.plugins.conversation.manifest import CONVERSATION_PLUGIN_MANIFEST
from xeren.plugins.conversation.provider import (
    ConversationProvider,
    DeterministicConversationProvider,
    LLMConversationProvider,
)
from xeren.plugins.conversation.schemas import (
    ConversationInput,
    ConversationIntent,
    ConversationResult,
    ConversationTone,
)
from xeren.plugins.errors import PluginExecutionError, PluginTimeoutError, PluginValidationError

logger = logging.getLogger("xeren.plugins.conversation.plugin")


class ConversationPlugin(BasePlugin):
    """Modular Conversational Plugin for natural everyday human interaction with Xeren."""

    def __init__(
        self,
        provider: Optional[ConversationProvider] = None,
        llm: Optional[BaseLLM] = None,
        safe_fallback_on_error: bool = True,
    ) -> None:
        self.safe_fallback_on_error = safe_fallback_on_error
        if provider is not None:
            self._provider = provider
        elif llm is not None:
            self._provider = LLMConversationProvider(llm=llm)
        else:
            self._provider = DeterministicConversationProvider()

    @property
    def manifest(self) -> PluginManifest:
        return CONVERSATION_PLUGIN_MANIFEST

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ConversationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ConversationResult

    @property
    def provider(self) -> ConversationProvider:
        """Active conversational response provider."""
        return self._provider

    def set_provider(self, provider: ConversationProvider) -> None:
        """Inject or swap the active conversational response provider."""
        self._provider = provider
        logger.info("ConversationPlugin provider updated to %s", type(provider).__name__)

    def set_llm(self, llm: BaseLLM) -> None:
        """Inject an LLM into the plugin, wrapping it in LLMConversationProvider."""
        if isinstance(self._provider, LLMConversationProvider):
            self._provider.set_llm(llm)
        else:
            self._provider = LLMConversationProvider(llm=llm)
        logger.info("ConversationPlugin LLM provider injected")

    def execute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Synchronously execute the conversational workflow."""
        start_time = time.perf_counter()

        # 1. Input validation
        validated: ConversationInput = self.validate_input(input_data)  # type: ignore

        # 2. Empty input handling: treat empty / whitespace message safely
        if not validated.message or not validated.message.strip():
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            empty_result = ConversationResult(
                response="It looks like your message was empty. How can I assist you today?",
                intent=ConversationIntent.CLARIFICATION,
                tone_used=validated.tone,
                clarification_needed=True,
                suggested_follow_ups=["Ask a question", "Request an explanation"],
                metadata={"reason": "empty_input"},
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=empty_result,
                latency_ms=latency_ms,
                metadata={"intent": ConversationIntent.CLARIFICATION.value},
            )

        # 3. Timeout bounds
        timeout = context.timeout_seconds if context and context.timeout_seconds else None

        # 4. Generate response with failure isolation
        try:
            if timeout is not None and timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._provider.generate_response, validated)
                    try:
                        result: ConversationResult = future.result(timeout=timeout)
                    except FuturesTimeoutError as timeout_err:
                        raise PluginTimeoutError(
                            f"ConversationPlugin execution timed out after {timeout}s",
                            plugin_name=self.name,
                            raw_error=timeout_err,
                        ) from timeout_err
            else:
                result = self._provider.generate_response(validated)

            # 5. Output schema validation
            validated_output = self.validate_output(result)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=validated_output,
                latency_ms=latency_ms,
                metadata={
                    "intent": result.intent.value,
                    "requires_tool": result.routing.requires_tool,
                    "tone": result.tone_used.value,
                },
            )

        except PluginTimeoutError as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning("ConversationPlugin timed out: %s", err)
            if not self.safe_fallback_on_error:
                raise
            return PluginExecutionResult(
                plugin_name=self.name,
                success=False,
                error=str(err),
                latency_ms=latency_ms,
                metadata={"error_type": "PluginTimeoutError"},
            )

        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning("ConversationPlugin provider error: %s", err)
            if not self.safe_fallback_on_error:
                raise PluginExecutionError(
                    f"ConversationPlugin execution failed: {err}",
                    plugin_name=self.name,
                    raw_error=err,
                ) from err

            # Safe structured fallback response so runtime is never left in an unhandled crash
            fallback_res = ConversationResult(
                response="I encountered an unexpected issue while generating a response. How else may I assist you?",
                intent=ConversationIntent.UNKNOWN,
                tone_used=validated.tone,
                clarification_needed=True,
                metadata={"error": str(err)},
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=fallback_res,
                error=str(err),
                latency_ms=latency_ms,
                metadata={"recovered_from_error": True},
            )

    async def aexecute(
        self,
        input_data: Union[BaseModel, Dict[str, Any]],
        context: Optional[PluginExecutionContext] = None,
    ) -> PluginExecutionResult:
        """Asynchronously execute conversational workflow."""
        start_time = time.perf_counter()
        validated: ConversationInput = self.validate_input(input_data)  # type: ignore

        if not validated.message or not validated.message.strip():
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            empty_result = ConversationResult(
                response="It looks like your message was empty. How can I assist you today?",
                intent=ConversationIntent.CLARIFICATION,
                tone_used=validated.tone,
                clarification_needed=True,
                metadata={"reason": "empty_input"},
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=empty_result,
                latency_ms=latency_ms,
            )

        timeout = context.timeout_seconds if context and context.timeout_seconds else None

        try:
            if timeout is not None and timeout > 0:
                result = await asyncio.wait_for(
                    self._provider.agenerate_response(validated),
                    timeout=timeout,
                )
            else:
                result = await self._provider.agenerate_response(validated)

            validated_output = self.validate_output(result)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=validated_output,
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError as timeout_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if not self.safe_fallback_on_error:
                raise PluginTimeoutError(
                    f"ConversationPlugin async execution timed out after {timeout}s",
                    plugin_name=self.name,
                    raw_error=timeout_err,
                ) from timeout_err
            return PluginExecutionResult(
                plugin_name=self.name,
                success=False,
                error=f"Execution timed out after {timeout}s",
                latency_ms=latency_ms,
            )

        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if not self.safe_fallback_on_error:
                raise PluginExecutionError(
                    f"ConversationPlugin async execution failed: {err}",
                    plugin_name=self.name,
                    raw_error=err,
                ) from err
            fallback_res = ConversationResult(
                response="I encountered an unexpected issue while generating a response. How else may I assist you?",
                intent=ConversationIntent.UNKNOWN,
                tone_used=validated.tone,
                clarification_needed=True,
                metadata={"error": str(err)},
            )
            return PluginExecutionResult(
                plugin_name=self.name,
                success=True,
                output=fallback_res,
                error=str(err),
                latency_ms=latency_ms,
            )

    def health_check(self) -> HealthCheckResult:
        start = time.perf_counter()
        return HealthCheckResult(
            status=PluginHealthStatus.HEALTHY,
            details={
                "name": self.name,
                "version": self.version,
                "provider": type(self._provider).__name__,
            },
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )


__all__ = ["ConversationPlugin"]
