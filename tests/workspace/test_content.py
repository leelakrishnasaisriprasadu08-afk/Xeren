"""Tests for WorkspaceContentRetriever: safe content retrieval, chunking, binary suppression, and secret redaction."""

from pathlib import Path

from xeren.workspace.content import WorkspaceContentRetriever
from xeren.workspace.permissions import WorkspacePermissionManager
from xeren.workspace.schemas import CandidateFile


def test_text_and_csv_safe_retrieval(tmp_path: Path):
    """Verify text and CSV retrieval parses content and structured previews."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("id,amount,region\n1,500,North\n2,800,South\n", encoding="utf-8")

    candidate = CandidateFile(
        file_id="sales_id",
        relative_path="sales.csv",
        absolute_path=csv_file.resolve(),
        file_type="csv",
        score=0.95,
        reason="sales data",
    )

    retriever = WorkspaceContentRetriever(permission_manager=manager)
    content = retriever.retrieve(candidate)

    assert content.is_binary is False
    assert content.content is not None
    assert "North" in content.content
    assert content.parsed_preview is not None
    assert content.parsed_preview.get("format") == "csv"
    assert content.parsed_preview.get("headers") == ["id", "amount", "region"]


def test_binary_file_suppresses_raw_bytes(tmp_path: Path):
    """Verify binary files do not dump raw binary bytes into retrieved content."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    bin_file = tmp_path / "binary_data.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04\xff\xfe\xfd" * 50)

    candidate = CandidateFile(
        file_id="bin_id",
        relative_path="binary_data.bin",
        absolute_path=bin_file.resolve(),
        file_type="bin",
        score=0.80,
        reason="binary test",
    )

    retriever = WorkspaceContentRetriever(permission_manager=manager)
    content = retriever.retrieve(candidate)

    assert content.is_binary is True
    assert content.content is None
    assert "warning" in content.metadata
    assert "Binary file detected" in content.metadata["warning"]


def test_file_size_limit_enforced(tmp_path: Path):
    """Verify files exceeding configured maximum size are flagged and not loaded."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    big_file = tmp_path / "big_data.txt"
    big_file.write_text("A" * 5000, encoding="utf-8")

    candidate = CandidateFile(
        file_id="big_id",
        relative_path="big_data.txt",
        absolute_path=big_file.resolve(),
        file_type="txt",
        score=0.85,
        reason="big file",
    )

    # Limit set to 2000 bytes
    retriever = WorkspaceContentRetriever(permission_manager=manager, max_file_size_bytes=2000)
    content = retriever.retrieve(candidate)

    assert content.content is None
    assert content.metadata.get("oversized") is True


def test_secret_redaction_in_retrieved_content(tmp_path: Path):
    """Verify secrets and keys inside retrieved files are redacted."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    config_file = tmp_path / "server_config.py"
    config_file.write_text(
        "API_KEY = 'sk-abcdefghijklmnopqrstuvwxyz123456'\n"
        "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        "DATABASE_URL = 'sqlite:///prod.db'\n",
        encoding="utf-8",
    )

    candidate = CandidateFile(
        file_id="cfg_id",
        relative_path="server_config.py",
        absolute_path=config_file.resolve(),
        file_type="py",
        score=0.80,
        reason="config",
    )

    retriever = WorkspaceContentRetriever(permission_manager=manager, redaction_enabled=True)
    content = retriever.retrieve(candidate)

    assert content.content is not None
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in content.content
    assert "AKIAIOSFODNN7EXAMPLE" not in content.content
    assert "[REDACTED" in content.content
    assert content.metadata.get("redacted_secrets") is True


def test_text_chunking(tmp_path: Path):
    """Verify chunking splits large text into overlapping windows."""
    manager = WorkspacePermissionManager()
    root = manager.authorize_root(tmp_path)

    long_file = tmp_path / "long_doc.md"
    long_file.write_text("Paragraph one. " * 300, encoding="utf-8")

    candidate = CandidateFile(
        file_id="long_id",
        relative_path="long_doc.md",
        absolute_path=long_file.resolve(),
        file_type="md",
        score=0.85,
        reason="long document",
    )

    retriever = WorkspaceContentRetriever(
        permission_manager=manager,
        default_chunk_size=500,
        default_chunk_overlap=50,
    )
    content = retriever.retrieve(candidate, chunk_content=True)

    assert len(content.chunks) > 1
    assert all(len(c) <= 500 for c in content.chunks)
