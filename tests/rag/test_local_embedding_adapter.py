"""Unit and integration tests for LocalOpenWeightEmbeddingAdapter using httpx transport mocking."""

import json
import httpx
import pytest

from xeren.models.errors import (
    InferenceTimeoutError,
    ModelNotFoundError,
    ProviderConnectionError,
    RateLimitError,
)
from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.config import EmbeddingConfig
from xeren.rag.embeddings.providers.local_openweight import LocalOpenWeightEmbeddingAdapter


@pytest.fixture
def base_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        model_id="nomic-embed-text",
        provider="local_openweight",
        api_base="http://localhost:11434/v1",
        batch_size=2,
    )


def test_local_embed_query_and_documents(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        req_data = json.loads(request.read())
        assert req_data["model"] == "nomic-embed-text"
        inputs = req_data["input"]

        resp_data = {
            "object": "list",
            "model": "nomic-embed-text",
            "data": [
                {"object": "embedding", "index": i, "embedding": [0.1 * (i + 1), 0.2, 0.3]}
                for i in range(len(inputs))
            ],
        }
        return httpx.Response(200, json=resp_data)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    # Query
    q_vec = adapter.embed_query("search term")
    assert q_vec == [0.1, 0.2, 0.3]

    # Documents with batching (batch_size=2, total=3 items -> 2 batches)
    docs = ["doc 1", "doc 2", "doc 3"]
    doc_vecs = adapter.embed_documents(docs)
    assert len(doc_vecs) == 3
    assert doc_vecs[0] == [0.1, 0.2, 0.3]
    assert doc_vecs[1] == [0.2, 0.2, 0.3]


@pytest.mark.asyncio
async def test_local_aembed_documents(base_config: EmbeddingConfig) -> None:
    async def ahandler(request: httpx.Request) -> httpx.Response:
        req_data = json.loads(request.read())
        inputs = req_data["input"]
        resp_data = {
            "data": [
                {"index": i, "embedding": [0.5, 0.5]}
                for i in range(len(inputs))
            ]
        }
        return httpx.Response(200, json=resp_data)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(ahandler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, async_client=async_client)

    vecs = await adapter.aembed_documents(["item 1", "item 2"])
    assert len(vecs) == 2
    assert vecs[0] == [0.5, 0.5]


def test_local_embed_chunks(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        req_data = json.loads(request.read())
        inputs = req_data["input"]
        return httpx.Response(
            200,
            json={"data": [{"index": i, "embedding": [0.1, 0.2, 0.3]} for i in range(len(inputs))]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    chunks = [
        DocumentChunk(document_id="doc1", content="Chunk A", chunk_index=0, total_chunks=2),
        DocumentChunk(document_id="doc1", content="Chunk B", chunk_index=1, total_chunks=2),
    ]

    embedded = adapter.embed_chunks(chunks)
    assert len(embedded) == 2
    assert embedded[0].chunk.content == "Chunk A"
    assert embedded[0].embedding == [0.1, 0.2, 0.3]
    assert embedded[0].embedding_model == "nomic-embed-text"


def test_local_embed_connection_error(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Endpoint unavailable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    with pytest.raises(ProviderConnectionError):
        adapter.embed_query("test")


def test_local_embed_timeout_error(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    with pytest.raises(InferenceTimeoutError):
        adapter.embed_query("test")


def test_local_embed_404_model_not_found(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Model not found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    with pytest.raises(ModelNotFoundError):
        adapter.embed_query("test")


def test_local_embed_429_rate_limit(base_config: EmbeddingConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too many requests")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = LocalOpenWeightEmbeddingAdapter(base_config, client=client)

    with pytest.raises(RateLimitError):
        adapter.embed_query("test")


def test_local_embed_ping(base_config: EmbeddingConfig) -> None:
    client_ok = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})))
    adapter_ok = LocalOpenWeightEmbeddingAdapter(base_config, client=client_ok)
    assert adapter_ok.ping() is True

    client_fail = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(500, text="Fail")))
    adapter_fail = LocalOpenWeightEmbeddingAdapter(base_config, client=client_fail)
    assert adapter_fail.ping() is False
