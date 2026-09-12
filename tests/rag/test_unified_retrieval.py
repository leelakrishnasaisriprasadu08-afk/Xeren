"""Unit and integration tests for UnifiedRetrievalEngine (CAG + MAG + RAG + Data Vault)."""

import pytest

from xeren.core.data_holding import PermittedDataHoldingVault
from xeren.core.vault import UserVault
from xeren.models.providers.mock import MockLLM
from xeren.models.config import ModelConfig
from xeren.rag.cag.engine import CAGRetrievalEngine
from xeren.rag.context.builder import ContextBuilder
from xeren.rag.document import Document, DocumentChunk
from xeren.rag.embeddings.providers.mock import MockEmbeddingModel
from xeren.rag.engine import RAGQueryEngine
from xeren.rag.mag.engine import MAGRetrievalEngine
from xeren.rag.retrieval.dense import DenseRetriever
from xeren.rag.stores.memory_store import InMemoryVectorStore
from xeren.rag.unified_engine import UnifiedRetrievalEngine
from xeren.security.schemas import DataSensitivityTier


@pytest.fixture
def setup_unified_environment(tmp_path):
    # 1. Setup local vault and permitted file
    vault_dir = tmp_path / "permitted_vault"
    vault_dir.mkdir()
    sample_file = vault_dir / "security_policy.txt"
    sample_file.write_text("Password length must be at least 16 characters.", encoding="utf-8")

    vault_db = tmp_path / "test_vault.db"
    user_vault = UserVault(db_path=vault_db)
    user_vault.grant_directory(vault_dir)

    holding_vault = PermittedDataHoldingVault(vault=user_vault)
    holding_vault.hold_device_file(file_path=sample_file, tier=DataSensitivityTier.LIBERAL)

    # 2. Setup MAG engine with constraints and episodic memories
    mag = MAGRetrievalEngine()
    mag.record_working_constraint("Enforce password security policy with strict error handling", session_id="session_test")
    mag.record_user_correction("Remember to include unit tests", session_id="session_test")

    # 3. Setup RAG engine with mock documents
    embedder = MockEmbeddingModel(dimension=32)
    store = InMemoryVectorStore()
    doc = Document.from_text("Security guidelines: Never log secrets in plaintext.", source="/docs/security.md")
    chunk = DocumentChunk(
        document_id=doc.id,
        content=doc.content,
        chunk_index=0,
        total_chunks=1,
        metadata={"source": "/docs/security.md", "title": "Security Guidelines"},
    )
    embedded = embedder.embed_chunks([chunk])
    store.add_chunks(embedded)
    retriever = DenseRetriever(embedding_model=embedder, vector_store=store)
    rag_engine = RAGQueryEngine(retriever=retriever, context_builder=ContextBuilder())

    # 4. Setup CAG engine
    cag = CAGRetrievalEngine()

    engine = UnifiedRetrievalEngine(
        cag_engine=cag,
        mag_engine=mag,
        rag_engine=rag_engine,
        vault=holding_vault,
    )

    return {
        "engine": engine,
        "vault": holding_vault,
        "sample_file": sample_file,
        "cag": cag,
        "mag": mag,
    }


def test_unified_retrieval_miss_then_hit(setup_unified_environment) -> None:
    env = setup_unified_environment
    engine: UnifiedRetrievalEngine = env["engine"]

    query = "What is the password policy for security?"

    # 1. First execution: Cache Miss, retrieves across MAG, Vault, and RAG
    payload_1 = engine.retrieve_context(query=query, session_id="session_test", use_cache=True)
    assert payload_1.is_cache_hit is False
    assert len(payload_1.vault_items) >= 1
    assert "Password length must be at least 16" in payload_1.formatted_prompt_context
    assert "--- BEGIN COGNITIVE MEMORY CONTEXT (MAG) ---" in payload_1.formatted_prompt_context
    assert "--- BEGIN PERMITTED DATA VAULT EXTRACTS ---" in payload_1.formatted_prompt_context
    assert "--- BEGIN GROUNDED CONTEXT ---" in payload_1.formatted_prompt_context

    # 2. Second execution: Cache Hit via CAG
    payload_2 = engine.retrieve_context(query=query, session_id="session_test", use_cache=True)
    assert payload_2.is_cache_hit is True
    assert payload_2.formatted_prompt_context == payload_1.formatted_prompt_context
    assert env["cag"].stats.hits == 1


def test_unified_retrieval_dynamic_invalidation_on_vault_update(setup_unified_environment) -> None:
    env = setup_unified_environment
    engine: UnifiedRetrievalEngine = env["engine"]
    sample_file = env["sample_file"]
    vault: PermittedDataHoldingVault = env["vault"]

    query = "password policy details"

    # Ingest query into cache
    p1 = engine.retrieve_context(query=query, session_id="session_test", use_cache=True)
    assert p1.is_cache_hit is False

    # Check cache hit
    p2 = engine.retrieve_context(query=query, session_id="session_test", use_cache=True)
    assert p2.is_cache_hit is True

    # Modify file and update vault
    sample_file.write_text("Password length updated to 24 characters minimum.", encoding="utf-8")
    vault.hold_device_file(file_path=sample_file)

    # Next retrieve will sync with vault and detect hash change, causing a cache miss and fresh retrieval
    p3 = engine.retrieve_context(query=query, session_id="session_test", use_cache=True)
    assert p3.is_cache_hit is False
    assert "Password length updated to 24" in p3.formatted_prompt_context


def test_unified_generate_response_scrubs_secrets(setup_unified_environment) -> None:
    env = setup_unified_environment
    engine: UnifiedRetrievalEngine = env["engine"]

    # Configure a mock LLM that attempts to output an exposed database URI and API key
    class LeakyMockLLM(MockLLM):
        def generate(self, messages, config=None, **kwargs):
            from xeren.models.types import ChatMessage, LLMResponse
            leak_text = "Here is your connection string: postgresql://admin:supersecretpassword@localhost:5432/prod_db with api_key='sk-123456789012345678901234567890'"
            return LLMResponse(
                content=leak_text,
                message=ChatMessage.assistant(leak_text),
                model_id="mock-leaky",
            )

    cfg = ModelConfig(model_id="mock-leaky", provider="mock")
    llm = LeakyMockLLM(config=cfg)

    answer = engine.generate_response(
        query="What is the database connection info?",
        llm=llm,
        session_id="session_test",
    )

    assert answer.scrubbed_sensitive_content is True
    assert "supersecretpassword" not in answer.content
    assert "sk-123456789012345678901234567890" not in answer.content
    assert "[REDACTED_CREDENTIAL]" in answer.content

    # Ensure interaction was recorded into MAG episodic memory
    mag = env["mag"]
    recent_memories = mag.get_memory_context("database connection", session_id="session_test")
    assert "User asked: What is the database connection info?" in recent_memories
