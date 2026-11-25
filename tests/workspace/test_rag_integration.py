"""Tests for Workspace Intelligence integration with existing Xeren RAG infrastructure."""

from pathlib import Path

from xeren.plugins.knowledge.plugin import KnowledgePlugin
from xeren.rag.pipeline import IngestionPipeline
from xeren.workspace.manager import WorkspaceManager
from xeren.workspace.schemas import CandidateFile, DiscoveryRequest


def test_discovered_file_ingests_into_existing_rag_pipeline(tmp_path: Path):
    """Verify discovered candidate file is ingested by existing IngestionPipeline without duplicating RAG."""
    manager = WorkspaceManager()
    manager.authorize_root(tmp_path)

    doc_path = tmp_path / "architecture.md"
    doc_path.write_text(
        "# Xeren Architecture\n"
        "Xeren features autonomous workspace discovery and modular plugins.\n",
        encoding="utf-8",
    )

    # 1. Discover file via WorkspaceManager
    discovery_res = manager.discover(DiscoveryRequest(goal="Find architecture document"))
    assert len(discovery_res.selected_candidates) == 1
    candidate = discovery_res.selected_candidates[0]

    # 2. Ingest candidate through existing IngestionPipeline
    pipeline = IngestionPipeline()
    chunk_ids = manager.ingest_into_rag(candidate, pipeline)

    assert len(chunk_ids) >= 1
    assert all(isinstance(cid, str) for cid in chunk_ids)


def test_discovered_file_ingests_into_existing_knowledge_plugin(tmp_path: Path):
    """Verify discovered candidate file is ingested into KnowledgePlugin and retrievable."""
    manager = WorkspaceManager()
    manager.authorize_root(tmp_path)

    paper_path = tmp_path / "quantum_paper.txt"
    paper_path.write_text(
        "Quantum computing enables exponential speedup for integer factorization via Shor's algorithm.",
        encoding="utf-8",
    )

    discovery_res = manager.discover(DiscoveryRequest(goal="Find quantum computing paper"))
    candidate = discovery_res.selected_candidates[0]

    knowledge = KnowledgePlugin()
    doc_ids = manager.ingest_into_rag(candidate, knowledge)

    assert len(doc_ids) == 1

    # Query knowledge plugin directly
    query_res = knowledge.query("What enables exponential speedup for integer factorization?")
    assert query_res.success is True
    assert len(query_res.retrieved_chunks) >= 1
    top_chunk = query_res.retrieved_chunks[0]
    assert "Shor's algorithm" in top_chunk.content
