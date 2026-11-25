"""End-to-end integration tests for Xeren RAG and LLM pipeline.

Validates the complete pipeline:
Document -> Chunk -> Embedding -> Vector Store -> Retrieve -> Rerank -> Context -> Ollama LLM -> Grounded Answer.
"""

import json
import httpx
import pytest

from xeren.eval.grounding import GroundingEvaluator
from xeren.eval.types import EvalSample
from xeren.models.config import LocalModelConfig
from xeren.models.errors import ProviderConnectionError
from xeren.models.providers.local_openweight import LocalOpenWeightAdapter
from xeren.rag.chunkers.recursive import RecursiveTextChunker
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import ContextConfig
from xeren.rag.document import Document
from xeren.rag.embeddings.config import EmbeddingConfig
from xeren.rag.embeddings.providers.local_openweight import LocalOpenWeightEmbeddingAdapter
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.generator import GroundedGenerator
from xeren.rag.pipeline import IngestionPipeline
from xeren.rag.rerankers.local import LocalReranker
from xeren.rag.rerankers.threshold import CompositeReranker, ScoreThresholdReranker
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.stores.memory_store import InMemoryVectorStore


def _mock_ollama_embedding_handler(request: httpx.Request) -> httpx.Response:
    """Mock Ollama /v1/embeddings endpoint producing deterministic embeddings."""
    body = json.loads(request.read())
    inputs = body.get("input", [])
    data = []
    for i, text in enumerate(inputs):
        text_lower = text.lower()
        if "xeren" in text_lower or "grounded" in text_lower or "rag" in text_lower:
            embedding = [0.9, 0.1, 0.0]
        elif "bread" in text_lower or "cake" in text_lower:
            embedding = [0.0, 0.1, 0.9]
        else:
            embedding = [0.1, 0.1, 0.1]
        data.append({"object": "embedding", "index": i, "embedding": embedding})

    return httpx.Response(200, json={"object": "list", "model": "nomic-embed-text", "data": data})


def _mock_ollama_llm_handler(request: httpx.Request) -> httpx.Response:
    """Mock Ollama /v1/chat/completions endpoint respecting grounded context prompt."""
    body = json.loads(request.read())
    messages = body.get("messages", [])
    user_content = messages[-1]["content"] if messages else ""

    if "--- BEGIN GROUNDED CONTEXT ---" in user_content and "Xeren" in user_content:
        content = (
            "Xeren is an AI system combining grounded RAG pipelines with local open-weight LLMs [1]."
        )
    else:
        content = (
            "I do not have enough information in the provided context to answer this question."
        )

    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-e2e-1",
            "model": "llama3.2:3b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 35,
                "completion_tokens": 18,
                "total_tokens": 53,
            },
        },
    )


@pytest.fixture
def e2e_pipeline_components():
    """Setup real pipeline components wired to Ollama adapters with mock transport."""
    embed_client = httpx.Client(transport=httpx.MockTransport(_mock_ollama_embedding_handler))
    llm_client = httpx.Client(transport=httpx.MockTransport(_mock_ollama_llm_handler))

    embed_config = EmbeddingConfig(
        provider="ollama",
        model_id="nomic-embed-text",
        api_base="http://localhost:11434/v1",
    )
    llm_config = LocalModelConfig(
        provider="ollama",
        model_id="llama3.2:3b",
        api_base="http://localhost:11434/v1",
    )

    embedder = LocalOpenWeightEmbeddingAdapter(config=embed_config, client=embed_client)
    llm = LocalOpenWeightAdapter(config=llm_config, client=llm_client)
    vector_store = InMemoryVectorStore()
    chunker = RecursiveTextChunker(chunk_size=200, chunk_overlap=20)
    retriever = DenseRetriever(embedding_model=embedder, vector_store=vector_store)
    reranker = CompositeReranker([LocalReranker(), ScoreThresholdReranker(min_score=0.4)])
    context_builder = ContextBuilder(ContextConfig(min_score_threshold=0.4))
    query_engine = RAGQueryEngine(
        retriever=retriever, reranker=reranker, context_builder=context_builder
    )
    generator = GroundedGenerator(query_engine=query_engine, llm=llm)

    return {
        "embedder": embedder,
        "llm": llm,
        "vector_store": vector_store,
        "chunker": chunker,
        "retriever": retriever,
        "reranker": reranker,
        "context_builder": context_builder,
        "query_engine": query_engine,
        "generator": generator,
    }


def test_pipeline_relevant_query_grounded_answer(e2e_pipeline_components) -> None:
    """Validate: Document -> Chunk -> Embedding -> Vector Store -> Retrieve -> Rerank -> Context -> Ollama -> Grounded Answer."""
    c = e2e_pipeline_components

    # 1. Document & Ingestion
    doc = Document.from_text(
        text="Xeren is an AI system combining grounded RAG pipelines with local open-weight LLMs.",
        source="docs/architecture.md",
        title="Xeren Architecture",
        extra={"author": "Xeren Core", "version": "1.0"},
    )
    chunks = c["chunker"].chunk(doc)
    embedded = c["embedder"].embed_chunks(chunks)
    c["vector_store"].add_chunks(embedded)

    # 2. Query execution through grounded generator
    answer = c["generator"].generate_answer("What is Xeren and how does it work?")

    # 3. Assertions on grounded answer
    assert answer.grounded_context.has_context is True
    assert len(answer.citations) >= 1
    assert "Xeren is an AI system" in answer.answer
    assert "[1]" in answer.answer
    assert answer.citations[0].source == "docs/architecture.md"
    assert answer.citations[0].title == "Xeren Architecture"
    assert answer.model_id == "llama3.2:3b"
    assert answer.finish_reason == "stop"
    assert answer.token_usage.total_tokens > 0

    # 4. Metric evaluation
    eval_result = GroundingEvaluator().evaluate(
        EvalSample(
            sample_id="e2e-relevant",
            query="What is Xeren and how does it work?",
            retrieved_chunks=answer.grounded_context.selected_chunks,
            generated_answer=answer.answer,
        )
    )
    assert eval_result.score > 0.4


def test_pipeline_irrelevant_query_insufficient_context(e2e_pipeline_components) -> None:
    """Validate: Irrelevant query filters out chunks and yields insufficient context response."""
    c = e2e_pipeline_components

    # Index technical document
    doc = Document.from_text(
        text="Xeren is an AI system combining grounded RAG pipelines with local open-weight LLMs.",
        source="docs/architecture.md",
        title="Xeren Architecture",
    )
    chunks = c["chunker"].chunk(doc)
    c["vector_store"].add_chunks(c["embedder"].embed_chunks(chunks))

    # Query about completely unrelated topic
    answer = c["generator"].generate_answer("How do you bake sourdough bread?")

    # Assertions: context filtered out, no citations, model signals insufficient context
    assert answer.grounded_context.has_context is False
    assert len(answer.citations) == 0
    assert "not have enough information" in answer.answer.lower()


def test_pipeline_empty_retrieval(e2e_pipeline_components) -> None:
    """Validate: Query against empty vector store completes gracefully with empty context."""
    c = e2e_pipeline_components

    # Vector store is empty (no indexing done)
    assert c["vector_store"].count() == 0

    answer = c["generator"].generate_answer("What is Xeren?")

    assert answer.grounded_context.has_context is False
    assert len(answer.citations) == 0
    assert answer.finish_reason == "stop"
    assert "not have enough information" in answer.answer.lower()


def test_pipeline_llm_unavailable_error(e2e_pipeline_components) -> None:
    """Validate: Unreachable Ollama LLM raises ProviderConnectionError."""
    c = e2e_pipeline_components

    doc = Document.from_text("Xeren data.", source="doc.txt")
    chunks = c["chunker"].chunk(doc)
    c["vector_store"].add_chunks(c["embedder"].embed_chunks(chunks))

    # LLM client with failing transport
    failing_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("Connection refused by Ollama"))
        )
    )
    unreachable_llm = LocalOpenWeightAdapter(c["llm"].config, client=failing_client)
    failing_generator = GroundedGenerator(query_engine=c["query_engine"], llm=unreachable_llm)

    with pytest.raises(ProviderConnectionError) as exc_info:
        failing_generator.generate_answer("What is Xeren?")

    assert "Cannot connect to local model server" in str(exc_info.value)


def test_pipeline_citations_provenance_preserved(e2e_pipeline_components) -> None:
    """Validate: Complete metadata and provenance chain is preserved from source to citation."""
    c = e2e_pipeline_components

    source_path = "specs/kernel_v2.md"
    doc_title = "Kernel Specification"
    extra_meta = {"module": "orchestration", "author": "Security Team"}

    doc = Document.from_text(
        text="The Xeren kernel provides robust isolation for task executions.",
        source=source_path,
        title=doc_title,
        extra=extra_meta,
    )

    # 1. Chunk preserves source document attributes
    chunks = c["chunker"].chunk(doc)
    assert chunks[0].document_id == doc.id
    assert chunks[0].metadata["source"] == source_path
    assert chunks[0].metadata["title"] == doc_title
    assert chunks[0].metadata["module"] == "orchestration"
    assert chunks[0].start_char_index is not None
    assert chunks[0].end_char_index is not None

    # 2. Ingest and execute query
    c["vector_store"].add_chunks(c["embedder"].embed_chunks(chunks))
    answer = c["generator"].generate_answer("How does the Xeren kernel isolate tasks?")

    # 3. Citation preserves full provenance
    assert len(answer.citations) == 1
    cit = answer.citations[0]
    assert cit.citation_id == 1
    assert cit.source == source_path
    assert cit.title == doc_title
    assert cit.chunk_id == chunks[0].chunk_id
    assert cit.start_char_index == chunks[0].start_char_index
    assert cit.end_char_index == chunks[0].end_char_index
    assert cit.metadata["module"] == "orchestration"
    assert cit.metadata["author"] == "Security Team"


@pytest.mark.asyncio
async def test_pipeline_async_flow() -> None:
    """Validate: Complete async pipeline execution with IngestionPipeline and GroundedGenerator."""
    async def a_embed_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        inputs = body.get("input", [])
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "nomic-embed-text",
                "data": [
                    {"object": "embedding", "index": i, "embedding": [0.8, 0.2, 0.0]}
                    for i in range(len(inputs))
                ],
            },
        )

    async def a_llm_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "llama3.2:3b",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "Async grounded answer [1]."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            },
        )

    embed_client = httpx.AsyncClient(transport=httpx.MockTransport(a_embed_handler))
    llm_client = httpx.AsyncClient(transport=httpx.MockTransport(a_llm_handler))

    embedder = LocalOpenWeightEmbeddingAdapter(
        EmbeddingConfig(provider="ollama", model_id="nomic-embed-text"),
        async_client=embed_client,
    )
    llm = LocalOpenWeightAdapter(
        LocalModelConfig(provider="ollama", model_id="llama3.2:3b"),
        async_client=llm_client,
    )
    store = InMemoryVectorStore()

    # IngestionPipeline
    pipeline = IngestionPipeline(
        chunker=RecursiveTextChunker(chunk_size=200, chunk_overlap=20),
        embedding_model=embedder,
        vector_store=store,
    )
    doc = Document.from_text(
        "Async ingestion of Xeren documentation.",
        source="async_doc.md",
        title="Async Guide",
    )
    inserted = await pipeline.aindex_document(doc)
    assert len(inserted) >= 1

    # Retrieval & Generation
    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    query_engine = RAGQueryEngine(
        retriever=retriever,
        reranker=LocalReranker(),
        context_builder=ContextBuilder(),
    )
    generator = GroundedGenerator(query_engine=query_engine, llm=llm)

    answer = await generator.agenerate_answer("Xeren documentation")
    assert answer.grounded_context.has_context is True
    assert len(answer.citations) >= 1
    assert "Async grounded answer" in answer.answer
