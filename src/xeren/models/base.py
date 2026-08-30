"""Abstract base interfaces for Xeren LLM and Embedding providers."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Iterator, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from xeren.models.config import ModelConfig
from xeren.models.errors import OutputParsingError
from xeren.models.types import ChatMessage, LLMResponse, StreamChunk

T = TypeVar("T", bound=BaseModel)


class BaseLLM(ABC):
    """Abstract base class for all LLM providers in Xeren."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    def _resolve_config(self, override_config: Optional[ModelConfig] = None) -> ModelConfig:
        """Merge default instance config with optional per-call override."""
        return override_config or self.config

    @abstractmethod
    def generate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronously generate a completion for the given chat messages."""
        pass

    @abstractmethod
    async def agenerate(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Asynchronously generate a completion for the given chat messages."""
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        """Synchronously stream incremental completion chunks."""
        pass

    @abstractmethod
    async def astream(
        self,
        messages: List[ChatMessage],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Asynchronously stream incremental completion chunks."""
        pass

    def generate_structured(
        self,
        messages: List[ChatMessage],
        schema: Type[T],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> T:
        """Generate structured data conforming to a Pydantic schema."""
        json_schema = json.dumps(schema.model_json_schema())
        schema_instruction = (
            f"\n\nRespond strictly with valid JSON conforming to this JSON schema:\n{json_schema}\n"
            "Do not include any additional commentary or markdown wrappers outside the raw JSON object."
        )

        augmented_messages = list(messages)
        if augmented_messages and augmented_messages[-1].content:
            last = augmented_messages[-1]
            augmented_messages[-1] = ChatMessage(
                role=last.role,
                content=last.content + schema_instruction,
                name=last.name,
                tool_calls=last.tool_calls,
                tool_call_id=last.tool_call_id,
                metadata=last.metadata,
            )
        else:
            augmented_messages.append(ChatMessage.user(schema_instruction))

        response = self.generate(augmented_messages, config=config, **kwargs)
        return self._parse_structured_json(response.content, schema)

    async def agenerate_structured(
        self,
        messages: List[ChatMessage],
        schema: Type[T],
        config: Optional[ModelConfig] = None,
        **kwargs: Any,
    ) -> T:
        """Asynchronously generate structured data conforming to a Pydantic schema."""
        json_schema = json.dumps(schema.model_json_schema())
        schema_instruction = (
            f"\n\nRespond strictly with valid JSON conforming to this JSON schema:\n{json_schema}\n"
            "Do not include any additional commentary or markdown wrappers outside the raw JSON object."
        )

        augmented_messages = list(messages)
        if augmented_messages and augmented_messages[-1].content:
            last = augmented_messages[-1]
            augmented_messages[-1] = ChatMessage(
                role=last.role,
                content=last.content + schema_instruction,
                name=last.name,
                tool_calls=last.tool_calls,
                tool_call_id=last.tool_call_id,
                metadata=last.metadata,
            )
        else:
            augmented_messages.append(ChatMessage.user(schema_instruction))

        response = await self.agenerate(augmented_messages, config=config, **kwargs)
        return self._parse_structured_json(response.content, schema)

    def _parse_structured_json(self, raw_text: str, schema: Type[T]) -> T:
        """Clean markdown markers and parse structured JSON into the Pydantic schema."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return schema.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError) as err:
            raise OutputParsingError(
                f"Failed to parse LLM response into schema {schema.__name__}: {err}",
                raw_output=raw_text,
                raw_error=err,
            ) from err

    def ping(self) -> bool:
        """Check provider connectivity and health."""
        return True

    async def aping(self) -> bool:
        """Asynchronously check provider connectivity and health."""
        return True


class BaseEmbeddingModel(ABC):
    """Abstract base class for embedding models in Xeren."""

    def __init__(self, config: Any = None) -> None:
        self.config = config

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate a dense vector embedding for a single query text."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for a batch of document texts."""
        pass

    def embed_text(self, text: str) -> List[float]:
        """Alias for embed_query."""
        return self.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Alias for embed_documents."""
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Asynchronously generate a dense vector embedding for a single query text."""
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Asynchronously generate dense vector embeddings for a batch of document texts."""
        return await asyncio.to_thread(self.embed_documents, texts)

    def ping(self) -> bool:
        """Check embedding provider health."""
        return True

    async def aping(self) -> bool:
        """Asynchronously check embedding provider health."""
        return True


__all__ = ["BaseLLM", "BaseEmbeddingModel"]
