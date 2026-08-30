"""Unit and integration tests for GroundedGenerator and GroundedAnswer."""

import pytest

from xeren.models.config import ModelConfig
from xeren.models.providers.mock import MockLLM
from xeren.rag.chunkers.markdown_header import MarkdownHeaderChunker
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import ContextConfig
from xeren.rag.document import Document
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.generator import GroundedAnswer, GroundedGenerator
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.stores.memory_store import InMemoryVectorStore


@pytest.fixture
def rag_generator() -> GroundedGenerator:
    embedder = MockEmbeddingModel(dimension=64)
    store = InMemoryVectorStore()

    doc_text = """# Architecture
## Security Subsystem
The security subsystem authorizes all external tool calls and permissions.
"""
    doc = Document.from_text(doc_text, source="/docs/arch.md", title="Architecture")
    chunks = MarkdownHeaderChunker().chunk(doc)
    store.add_chunks(embedder.embed_chunks(chunks))

    retriever = DenseRetriever(embedder, store)
    context_builder = ContextBuilder(ContextConfig(min_score_threshold=-1.0))
    query_engine = RAGQueryEngine(retriever=retriever, context_builder=context_builder)

    llm = MockLLM(
        config=ModelConfig(model_id="mock-gpt", provider="mock"),
        canned_response="The security subsystem authorizes all external tool calls according to [1].",
        stream_chunks=["The security", " subsystem authorizes", " all tool calls [1]."],
    )

    return GroundedGenerator(query_engine=query_engine, llm=llm)


def test_grounded_generator_sync(rag_generator: GroundedGenerator) -> None:
    answer: GroundedAnswer = rag_generator.generate_answer("How does security work?")

    assert answer.query == "How does security work?"
    assert "The security subsystem authorizes" in answer.answer
    assert answer.grounded_context.has_context is True
    assert len(answer.citations) >= 1
    assert answer.citations[0].source == "/docs/arch.md"
    assert answer.latency_ms >= 0.0
    assert answer.token_usage.total_tokens > 0
    assert answer.model_id == "mock-gpt"
    assert answer.finish_reason == "stop"


@pytest.mark.asyncio
async def test_grounded_generator_async(rag_generator: GroundedGenerator) -> None:
    answer: GroundedAnswer = await rag_generator.agenerate_answer("How does security work?")

    assert "The security subsystem authorizes" in answer.answer
    assert len(answer.citations) >= 1
    assert answer.latency_ms >= 0.0


def test_grounded_generator_stream(rag_generator: GroundedGenerator) -> None:
    context, stream_iter = rag_generator.stream_answer("How does security work?")

    assert context.has_context is True
    chunks = list(stream_iter)
    assert len(chunks) >= 2
    full_text = "".join(c.delta_content for c in chunks)
    assert "The security subsystem authorizes all tool calls [1]." in full_text


@pytest.mark.asyncio
async def test_grounded_generator_astream(rag_generator: GroundedGenerator) -> None:
    context, astream_iter = await rag_generator.astream_answer("How does security work?")

    assert context.has_context is True
    chunks = []
    async for c in astream_iter:
        chunks.append(c)

    full_text = "".join(c.delta_content for c in chunks)
    assert "The security subsystem authorizes all tool calls [1]." in full_text
