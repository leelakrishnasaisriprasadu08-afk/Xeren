"""SQLite DDL schema definitions for Xeren Sovereign Knowledge DB."""

import sqlite3

SCHEMA_DDL = """
-- Layer 1: Source Layer
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    title TEXT,
    content_hash TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    lifecycle_state TEXT NOT NULL DEFAULT 'INGESTED',
    owner TEXT NOT NULL DEFAULT 'sovereign_user',
    workspace_id TEXT NOT NULL DEFAULT 'default',
    access_level TEXT NOT NULL DEFAULT 'LIBERAL',
    sensitivity_tier TEXT NOT NULL DEFAULT 'INTERNAL',
    retention_policy TEXT DEFAULT 'FOREVER',
    superseded_by_doc_id TEXT DEFAULT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
    FOREIGN KEY (superseded_by_doc_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS document_versions (
    version_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    content_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    change_summary TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    UNIQUE (document_id, version_number)
);

-- Layer 2: Knowledge Layer
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    section_title TEXT,
    page_number INTEGER,
    parent_chunk_id TEXT,
    content_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_chunk_id) REFERENCES chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS knowledge_relationships (
    relationship_id TEXT PRIMARY KEY,
    source_chunk_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    target_chunk_id TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_reference TEXT,
    model_id TEXT DEFAULT 'xeren_ingest',
    created_by TEXT DEFAULT 'system',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    FOREIGN KEY (source_chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    FOREIGN KEY (target_chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence (
    evidence_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    relevance_score REAL NOT NULL DEFAULT 1.0,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    verified_by_model TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS provenance (
    provenance_id TEXT PRIMARY KEY,
    claim_id TEXT,
    chunk_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    document_version INTEGER NOT NULL,
    page_number INTEGER,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id) ON DELETE SET NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retrieval_events (
    event_id TEXT PRIMARY KEY,
    query_id TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    query_text TEXT,
    chunk_id TEXT NOT NULL,
    retrieval_method TEXT NOT NULL,
    rank_position INTEGER NOT NULL,
    score REAL NOT NULL,
    user_or_task_id TEXT,
    workspace_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

-- Layer 3: Index Layer
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    index_id TEXT NOT NULL,
    vector_blob BLOB,
    version INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    UNIQUE (chunk_id, model_id, version)
);

CREATE TABLE IF NOT EXISTS lexical_index (
    chunk_id TEXT NOT NULL,
    term TEXT NOT NULL,
    term_frequency REAL NOT NULL,
    document_frequency INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (chunk_id, term),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

-- Performance indices
CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_docs_state ON documents(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_docs_workspace ON documents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_rel_source ON knowledge_relationships(source_chunk_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_rel_target ON knowledge_relationships(target_chunk_id);
CREATE INDEX IF NOT EXISTS idx_provenance_chunk ON provenance(chunk_id);
CREATE INDEX IF NOT EXISTS idx_provenance_claim ON provenance(claim_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_query_hash ON retrieval_events(query_hash);
CREATE INDEX IF NOT EXISTS idx_lexical_term ON lexical_index(term);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize all relational tables, foreign key constraints, and indices."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_DDL)
    conn.commit()
