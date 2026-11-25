"""Codebase Indexer for Xeren RAG CAN.

Populates both SQLite `code_chunks` (for BM25 lexical search) and
Qdrant `xeren_codebase` (for Dense vector semantic search).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xeren.rag.indexer")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = Path(os.getenv("XEREN_DB_PATH", str(PROJECT_ROOT / "data" / "xeren.db")))
DEFAULT_QDRANT_PATH = Path(os.getenv("XEREN_QDRANT_PATH", str(PROJECT_ROOT / "data" / "qdrant_storage")))
COLLECTION_NAME = "xeren_codebase"
EMBEDDING_DIM = 384


def ensure_sqlite_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS code_chunks (
            id TEXT PRIMARY KEY,
            filepath TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    conn.commit()


def chunk_file(file_path: Path, max_lines: int = 40, overlap: int = 5) -> List[Dict[str, Any]]:
    """Chunks a file into overlapping line segments."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Could not read %s: %s", file_path, exc)
        return []

    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    chunks: List[Dict[str, Any]] = []
    rel_path = str(file_path).replace("\\", "/")
    step = max(1, max_lines - overlap)

    for i in range(0, len(lines), step):
        chunk_lines = lines[i : i + max_lines]
        chunk_text = "".join(chunk_lines).strip()
        if not chunk_text:
            continue

        chunk_id = f"{file_path.stem}_{i}_{uuid.uuid4().hex[:6]}"
        chunks.append(
            {
                "id": chunk_id,
                "filepath": rel_path,
                "start_line": i + 1,
                "end_line": min(i + len(chunk_lines), len(lines)),
                "content": chunk_text,
                "metadata": json.dumps({"start_line": i + 1, "end_line": min(i + len(chunk_lines), len(lines))}),
            }
        )
        if i + max_lines >= len(lines):
            break

    return chunks


def index_directory(
    root_dir: Path,
    db_path: Path = DEFAULT_DB_PATH,
    qdrant_path: Path = DEFAULT_QDRANT_PATH,
    file_extensions: Optional[List[str]] = None,
) -> int:
    """Indexes all matching files in root_dir into SQLite and Qdrant."""
    if file_extensions is None:
        file_extensions = [".py", ".md", ".json", ".yaml", ".yml", ".toml"]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    qdrant_path.mkdir(parents=True, exist_ok=True)

    # 1. Collect files
    files: List[Path] = []
    for ext in file_extensions:
        files.extend(root_dir.rglob(f"*{ext}"))

    # Filter out venvs, caches, checkpoints
    ignored_patterns = {".venv", "__pycache__", ".git", "checkpoints", "qdrant_storage"}
    filtered_files = [
        f for f in files if not any(part in ignored_patterns for part in f.parts) and f.is_file()
    ]
    logger.info("Found %d eligible files to index in %s", len(filtered_files), root_dir)

    all_chunks: List[Dict[str, Any]] = []
    for f in filtered_files:
        all_chunks.extend(chunk_file(f))

    logger.info("Generated %d code chunks from %d files", len(all_chunks), len(filtered_files))
    if not all_chunks:
        return 0

    # 2. Store in SQLite
    conn = sqlite3.connect(str(db_path))
    ensure_sqlite_table(conn)
    cursor = conn.cursor()

    for chunk in all_chunks:
        cursor.execute(
            """
            INSERT OR REPLACE INTO code_chunks (id, filepath, content, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (chunk["id"], chunk["filepath"], chunk["content"], chunk["metadata"]),
        )
    conn.commit()
    conn.close()
    logger.info("Stored %d chunks in SQLite at %s", len(all_chunks), db_path)

    # 3. Embed & Store in Qdrant
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams
        from sentence_transformers import SentenceTransformer

        logger.info("Generating embeddings with SentenceTransformer('all-MiniLM-L6-v2')...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        client = QdrantClient(path=str(qdrant_path))

        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

        # Batch encode
        batch_size = 64
        for b_start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[b_start : b_start + batch_size]
            texts = [c["content"] for c in batch]
            embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

            points = []
            for item, emb in zip(batch, embeddings):
                points.append(
                    PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, item["id"])),
                        vector=emb.tolist(),
                        payload={
                            "id": item["id"],
                            "filepath": item["filepath"],
                            "content": item["content"],
                            "metadata": item["metadata"],
                        },
                    )
                )
            client.upsert(collection_name=COLLECTION_NAME, points=points)

        client.close()
        logger.info("Successfully indexed %d chunks into Qdrant collection '%s'", len(all_chunks), COLLECTION_NAME)
    except Exception as exc:
        logger.error("Failed to index into Qdrant: %s", exc)

    return len(all_chunks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Index codebase files into SQLite and Qdrant")
    parser.add_argument("--dir", type=str, default=str(PROJECT_ROOT / "src"), help="Directory to index")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--qdrant", type=str, default=str(DEFAULT_QDRANT_PATH), help="Qdrant storage path")
    args = parser.parse_args()

    count = index_directory(
        root_dir=Path(args.dir),
        db_path=Path(args.db),
        qdrant_path=Path(args.qdrant),
    )
    print(f"[*] Complete. Indexed {count} chunks.")
