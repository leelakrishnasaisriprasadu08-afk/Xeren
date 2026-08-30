"""Full RAG generation engine combining retrieval, context construction, and LLM synthesis."""

import time
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple
from pydantic import BaseModel, Field

from xeren.models.base import BaseLLM
from xeren.models.config import ModelConfig
from xeren.models.types import ChatMessage, Role, StreamChunk, TokenUsage
from xeren.rag.context.types import Citation, GroundedContext
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.retrieval.filter import MetadataFilter


class GroundedAnswer(BaseModel):
    """Generated answer payload containing the model output, citations, latency, and token usage."""

    answer: str = Field(..., description="Generated text answer")
    query: str = Field(..., description="Original user query")
    grounded_context: GroundedContext = Field(..., description="Assembled grounded context")
    citations: List[Citation] = Field(default_factory=list, description="Extracted source citations")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Total generation latency in milliseconds")
    token_usage: TokenUsage = Field(default_factory=TokenUsage, description="Token consumption accounting")
    model_id: str = Field(default="", description="ID of the model that generated this answer")
    finish_reason: str = Field(default="stop", description="Generation completion reason")
    raw_response: Dict[str, Any] = Field(default_factory=dict, description="Raw provider response")


class GroundedGenerator:
    """Full RAG orchestrator integrating retrieval, context assembly, and LLM generation."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are an accurate, reliable, and truthful assistant.\n"
        "Answer the user's question strictly using the information provided in the grounded context below.\n"
        "Cite sources using bracketed notation like [1], [2] corresponding to the provided citations.\n"
        "If the provided context does not contain sufficient information to answer, state clearly that you do not have enough information."
    )

    def __init__(
        self,
        query_engine: RAGQueryEngine,
        llm: BaseLLM,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.query_engine = query_engine
        self.llm = llm
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    def _build_messages(self, query: str, context: GroundedContext) -> List[ChatMessage]:
        messages = [ChatMessage.system(self.system_prompt)]
        if context.has_context:
            user_prompt = f"{context.formatted_text}\n\nQuestion: {query}\nAnswer:"
        else:
            user_prompt = f"Question: {query}\nAnswer:"
        messages.append(ChatMessage.user(user_prompt))
        return messages

    def generate_answer(
        self,
        query: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
        llm_config: Optional[ModelConfig] = None,
    ) -> GroundedAnswer:
        """Execute RAG retrieval and generate a grounded, cited answer."""
        start_time = time.perf_counter()

        # 1. Retrieve & construct context
        grounded_context = self.query_engine.query(query, top_k=top_k, top_n=top_n, filter=filter)

        # 2. Build prompt messages
        messages = self._build_messages(query, grounded_context)

        # 3. Generate response with LLM
        response = self.llm.generate(messages, config=llm_config)
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return GroundedAnswer(
            answer=response.content,
            query=query,
            grounded_context=grounded_context,
            citations=grounded_context.citations,
            latency_ms=latency_ms,
            token_usage=response.usage,
            model_id=response.model_id or self.llm.config.model_id,
            finish_reason=response.finish_reason,
            raw_response=response.raw_response,
        )

    async def agenerate_answer(
        self,
        query: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
        llm_config: Optional[ModelConfig] = None,
    ) -> GroundedAnswer:
        """Asynchronously execute RAG retrieval and generate a grounded, cited answer."""
        start_time = time.perf_counter()

        # 1. Async retrieve & construct context
        grounded_context = await self.query_engine.aquery(query, top_k=top_k, top_n=top_n, filter=filter)

        # 2. Build prompt messages
        messages = self._build_messages(query, grounded_context)

        # 3. Async generate response with LLM
        response = await self.llm.agenerate(messages, config=llm_config)
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return GroundedAnswer(
            answer=response.content,
            query=query,
            grounded_context=grounded_context,
            citations=grounded_context.citations,
            latency_ms=latency_ms,
            token_usage=response.usage,
            model_id=response.model_id or self.llm.config.model_id,
            finish_reason=response.finish_reason,
            raw_response=response.raw_response,
        )

    def stream_answer(
        self,
        query: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
        llm_config: Optional[ModelConfig] = None,
    ) -> Tuple[GroundedContext, Iterator[StreamChunk]]:
        """Retrieve grounded context and stream the generated response chunks."""
        grounded_context = self.query_engine.query(query, top_k=top_k, top_n=top_n, filter=filter)
        messages = self._build_messages(query, grounded_context)
        stream_iter = self.llm.stream(messages, config=llm_config)
        return grounded_context, stream_iter

    async def astream_answer(
        self,
        query: str,
        top_k: int = 10,
        top_n: Optional[int] = 5,
        filter: Optional[MetadataFilter] = None,
        llm_config: Optional[ModelConfig] = None,
    ) -> Tuple[GroundedContext, AsyncIterator[StreamChunk]]:
        """Asynchronously retrieve grounded context and stream generated response chunks."""
        grounded_context = await self.query_engine.aquery(query, top_k=top_k, top_n=top_n, filter=filter)
        messages = self._build_messages(query, grounded_context)
        astream_iter = self.llm.astream(messages, config=llm_config)
        return grounded_context, astream_iter
