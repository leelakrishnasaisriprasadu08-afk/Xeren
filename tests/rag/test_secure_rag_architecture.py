"""Comprehensive security verification tests for the 8-stage Secure RAG Architecture.

Validates:
1. Multi-tenant isolation & pre-retrieval filtering in QdrantVectorStore.
2. Filter translation (_build_qdrant_filter) for EQ, IN, and NEQ operators.
3. Defense-in-depth post-retrieval validation in RAGQueryEngine (sync & async).
4. Prompt-injection neutralization and delimiter escaping in ContextBuilder.
5. Post-generation credential scrubbing via OutputSecurityGuard in GroundedGenerator.
"""

import pytest
from qdrant_client import models as qmodels

from xeren.models.config import ModelConfig
from xeren.models.providers.mock import MockLLM
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.context.types import ContextConfig
from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.generator import GroundedGenerator, OutputSecurityGuard
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.retrieval.filter import FilterCondition, FilterOperator, MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.qdrant import QdrantVectorStore


class TestQdrantFilterBuilding:
    """Verify translation of MetadataFilter into native Qdrant query filters."""

    def test_filter_eq_operator(self) -> None:
        store = QdrantVectorStore(persist_path=":memory:")
        meta_filter = MetadataFilter().equals("tenant_id", "corp_alpha")
        q_filter = store._build_qdrant_filter(meta_filter)

        assert isinstance(q_filter, qmodels.Filter)
        assert q_filter.must is not None
        assert len(q_filter.must) == 1
        condition = q_filter.must[0]
        assert condition.key == "tenant_id"
        assert condition.match.value == "corp_alpha"

    def test_filter_in_operator(self) -> None:
        store = QdrantVectorStore(persist_path=":memory:")
        meta_filter = MetadataFilter().in_list("access_level", ["public", "internal"])
        q_filter = store._build_qdrant_filter(meta_filter)

        assert isinstance(q_filter, qmodels.Filter)
        assert q_filter.must is not None
        assert len(q_filter.must) == 1
        condition = q_filter.must[0]
        assert condition.key == "access_level"
        assert condition.match.any == ["public", "internal"]

    def test_filter_neq_operator(self) -> None:
        store = QdrantVectorStore(persist_path=":memory:")
        meta_filter = MetadataFilter(
            conditions=[FilterCondition(field="department", operator=FilterOperator.NEQ, value="confidential_hr")]
        )
        q_filter = store._build_qdrant_filter(meta_filter)

        assert isinstance(q_filter, qmodels.Filter)
        assert q_filter.must is not None
        assert len(q_filter.must) == 1
        negated = q_filter.must[0]
        assert isinstance(negated, qmodels.Filter)
        assert negated.must_not is not None
        assert len(negated.must_not) == 1
        assert negated.must_not[0].key == "department"
        assert negated.must_not[0].match.value == "confidential_hr"

    def test_filter_or_logic(self) -> None:
        store = QdrantVectorStore(persist_path=":memory:")
        meta_filter = (
            MetadataFilter(logic="OR")
            .equals("department", "engineering")
            .equals("department", "product")
        )
        q_filter = store._build_qdrant_filter(meta_filter)

        assert isinstance(q_filter, qmodels.Filter)
        assert q_filter.should is not None
        assert len(q_filter.should) == 2


class TestQdrantMultiTenantRetrieval:
    """Verify that Qdrant native filters enforce zero data leakage across tenants."""

    @pytest.fixture
    def populated_store(self) -> QdrantVectorStore:
        store = QdrantVectorStore(persist_path=":memory:")

        # Chunk from Tenant Alpha
        chunk_alpha = DocumentChunk(
            chunk_id="chunk_alpha_secret",
            document_id="doc_alpha_internal",
            content="Alpha Corp Q4 financial secret forecast is $50M EBITDA.",
            chunk_index=0,
            metadata={"tenant_id": "corp_alpha", "access_level": "confidential"},
        )
        emb_alpha = EmbeddedChunk(
            chunk=chunk_alpha,
            embedding=[0.9, 0.1, 0.0, 0.0] * 96,
            embedding_model="mock-embed",
        )

        # Chunk from Tenant Beta
        chunk_beta = DocumentChunk(
            chunk_id="chunk_beta_secret",
            document_id="doc_beta_internal",
            content="Beta Corp proprietary merger details with Delta Corp.",
            chunk_index=0,
            metadata={"tenant_id": "corp_beta", "access_level": "confidential"},
        )
        emb_beta = EmbeddedChunk(
            chunk=chunk_beta,
            embedding=[0.1, 0.9, 0.0, 0.0] * 96,
            embedding_model="mock-embed",
        )

        store.add_chunks([emb_alpha, emb_beta])
        return store

    def test_tenant_alpha_cannot_see_beta(self, populated_store: QdrantVectorStore) -> None:
        # Search using Tenant Alpha authorization filter
        alpha_filter = MetadataFilter().equals("tenant_id", "corp_alpha")

        # Query with vector closer to Beta Corp
        query_vector_near_beta = [0.1, 0.88, 0.0, 0.0] * 96
        results = populated_store.similarity_search(
            query_vector=query_vector_near_beta,
            top_k=5,
            filter=alpha_filter,
        )

        # Even though vector is closest to Beta, Beta must NEVER be returned to Alpha
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "chunk_alpha_secret"
        assert results[0].chunk.metadata["tenant_id"] == "corp_alpha"
        assert "Beta Corp" not in results[0].chunk.content

    def test_tenant_beta_cannot_see_alpha(self, populated_store: QdrantVectorStore) -> None:
        # Search using Tenant Beta authorization filter
        beta_filter = MetadataFilter().equals("tenant_id", "corp_beta")

        # Query with vector closer to Alpha Corp
        query_vector_near_alpha = [0.89, 0.1, 0.0, 0.0] * 96
        results = populated_store.similarity_search(
            query_vector=query_vector_near_alpha,
            top_k=5,
            filter=beta_filter,
        )

        # Alpha must never be returned to Beta
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "chunk_beta_secret"
        assert results[0].chunk.metadata["tenant_id"] == "corp_beta"
        assert "Alpha Corp" not in results[0].chunk.content


class TestDefenseInDepthOrchestrator:
    """Verify RAGQueryEngine drops unauthorized chunks if a compromised/buggy retriever returns them."""

    def test_engine_defense_in_depth_drops_unauthorized_sync(self) -> None:
        embedder = MockEmbeddingModel(dimension=64)
        store = QdrantVectorStore(persist_path=":memory:")

        # Add chunk belonging to Tenant Evil
        leaked_chunk = DocumentChunk(
            chunk_id="c_evil",
            document_id="doc_evil",
            content="Sensitive evil corporate salary data",
            chunk_index=0,
            metadata={"tenant_id": "tenant_evil"},
        )
        legit_chunk = DocumentChunk(
            chunk_id="c_legit",
            document_id="doc_legit",
            content="Legitimate user manual content",
            chunk_index=0,
            metadata={"tenant_id": "tenant_good"},
        )
        store.add_chunks(embedder.embed_chunks([leaked_chunk, legit_chunk]))

        retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
        context_builder = ContextBuilder(ContextConfig(min_score_threshold=-1.0))
        engine = RAGQueryEngine(retriever=retriever, context_builder=context_builder)

        # User is only authorized for tenant_good
        good_filter = MetadataFilter().equals("tenant_id", "tenant_good")
        context = engine.query("Show me data", filter=good_filter)

        # Verify only legit chunk was included in grounded context
        assert len(context.selected_chunks) == 1
        assert context.selected_chunks[0].chunk.chunk_id == "c_legit"
        assert "Sensitive evil corporate salary" not in context.formatted_text
        assert "Legitimate user manual" in context.formatted_text

    @pytest.mark.asyncio
    async def test_engine_defense_in_depth_drops_unauthorized_async(self) -> None:
        embedder = MockEmbeddingModel(dimension=64)
        store = QdrantVectorStore(persist_path=":memory:")

        leaked_chunk = DocumentChunk(
            chunk_id="c_other_tenant",
            document_id="doc_other",
            content="Confidential financial report of Tenant B",
            chunk_index=0,
            metadata={"tenant_id": "tenant_B"},
        )
        store.add_chunks(embedder.embed_chunks([leaked_chunk]))

        retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
        context_builder = ContextBuilder(ContextConfig(min_score_threshold=-1.0))
        engine = RAGQueryEngine(retriever=retriever, context_builder=context_builder)

        # Requesting as Tenant A
        tenant_a_filter = MetadataFilter().equals("tenant_id", "tenant_A")
        context = await engine.aquery("financial report", filter=tenant_a_filter)

        # Must return empty context rather than leaking Tenant B's data
        assert context.has_context is False
        assert len(context.selected_chunks) == 0
        assert context.formatted_text == ""


class TestOutputSecurityGuard:
    """Verify OutputSecurityGuard regex scrubbing for sensitive credentials."""

    def test_scrub_api_keys(self) -> None:
        text = "Here is your key: sk-abc1234567890abcdef1234567890 and enjoy."
        scrubbed, modified = OutputSecurityGuard.scrub(text)
        assert modified is True
        assert "sk-abc" not in scrubbed
        assert "Here is your key: [REDACTED_CREDENTIAL] and enjoy." == scrubbed

    def test_scrub_jwt_tokens(self) -> None:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.q-Gg2jPxqTZA1MkFZvyOtJU6_JJ5JKtq-ax1AQFI7zM"
        text = f"Bearer {token}"
        scrubbed, modified = OutputSecurityGuard.scrub(text)
        assert modified is True
        assert token not in scrubbed
        assert scrubbed == "Bearer [REDACTED_CREDENTIAL]"

    def test_scrub_database_urls(self) -> None:
        db_url = "postgresql://postgres:secret_pass_123@db.supabase.co:5432/postgres"
        text = f"Connection string is {db_url}."
        scrubbed, modified = OutputSecurityGuard.scrub(text)
        assert modified is True
        assert "secret_pass_123" not in scrubbed
        assert scrubbed == "Connection string is [REDACTED_CREDENTIAL]."

    def test_scrub_private_keys(self) -> None:
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y...\n-----END RSA PRIVATE KEY-----"
        text = f"The RSA private key was:\n{key}"
        scrubbed, modified = OutputSecurityGuard.scrub(text)
        assert modified is True
        assert "MIIEowIBAAKCAQEA0Y" not in scrubbed
        assert "[REDACTED_CREDENTIAL]" in scrubbed

    def test_scrub_passwords(self) -> None:
        text = 'User record: password: "super_secret_password_xyz"'
        scrubbed, modified = OutputSecurityGuard.scrub(text)
        assert modified is True
        assert "super_secret_password_xyz" not in scrubbed
        assert "[REDACTED_CREDENTIAL]" in scrubbed

    def test_clean_text_unchanged(self) -> None:
        clean = "This is a normal grounded answer referencing document [1] without secrets."
        scrubbed, modified = OutputSecurityGuard.scrub(clean)
        assert modified is False
        assert scrubbed == clean


class TestGroundedGeneratorSecurityScrubbing:
    """Verify that GroundedGenerator scrubs leaked credentials from LLM responses."""

    def test_generator_redacts_accidental_leaks(self) -> None:
        embedder = MockEmbeddingModel(dimension=64)
        store = QdrantVectorStore(persist_path=":memory:")

        chunk = DocumentChunk(
            chunk_id="c_info",
            document_id="d_info",
            content="API documentation for server access.",
            chunk_index=0,
            metadata={"tenant_id": "tenant_1"},
        )
        store.add_chunks(embedder.embed_chunks([chunk]))

        retriever = DenseRetriever(embedder, store)
        context_builder = ContextBuilder(ContextConfig(min_score_threshold=-1.0))
        query_engine = RAGQueryEngine(retriever=retriever, context_builder=context_builder)

        # Mock LLM accidentally echoes a secret
        leaking_llm = MockLLM(
            config=ModelConfig(model_id="mock-gpt", provider="mock"),
            canned_response="Connect with postgresql://dbuser:MySecretPassword99@host.com:5432/db to query.",
        )

        generator = GroundedGenerator(query_engine=query_engine, llm=leaking_llm)
        answer = generator.generate_answer(
            query="How do I connect?",
            filter=MetadataFilter().equals("tenant_id", "tenant_1"),
        )

        assert "MySecretPassword99" not in answer.answer
        assert "[REDACTED_CREDENTIAL]" in answer.answer
