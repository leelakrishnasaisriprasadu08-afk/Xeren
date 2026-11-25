"""Dense Vector Search Worker MCP Server.

Provides semantic embedding retrieval over Qdrant using sentence-transformers (all-MiniLM-L6-v2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing FastMCP from official MCP SDK, provide fallback mock if unavailable
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    class FastMCP:  # type: ignore[no-redef]
        """Fallback FastMCP implementation when mcp package is pending installation."""
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: Dict[str, Any] = {}

        def tool(self, name: Optional[str] = None):
            def decorator(func):
                tool_name = name or func.__name__
                self.tools[tool_name] = func
                return func
            return decorator

        def run(self) -> None:
            print(f"[{self.name}] Running in standalone fallback mode.")


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_PATH = Path(os.getenv("XEREN_QDRANT_PATH", str(PROJECT_ROOT / "data" / "qdrant_storage")))
DEFAULT_COLLECTION = "xeren_codebase"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# Initialize MCP server
mcp = FastMCP("Dense_Vector_Search")


class DenseVectorWorker:
    """Manages dense vector embeddings and semantic search via Qdrant."""

    def __init__(
        self,
        storage_path: Path = DEFAULT_STORAGE_PATH,
        collection_name: str = DEFAULT_COLLECTION,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.collection_name = collection_name
        self.model_name = model_name
        self._model = None
        self._client = None

    @property
    def model(self):
        """Lazy load SentenceTransformer encoder."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def client(self):
        """Lazy load QdrantClient with local persistent storage path."""
        if self._client is None:
            from qdrant_client import QdrantClient
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(self.storage_path))
        return self._client

    def ensure_collection(self, vector_dim: int = 384) -> None:
        """Ensure collection exists in Qdrant storage."""
        try:
            from qdrant_client import models
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_dim,
                        distance=models.Distance.COSINE,
                    ),
                )
        except ImportError:
            # Fallback when running in environments where qdrant_client is pending installation
            pass


    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Compute query embedding and retrieve nearest neighbors from Qdrant."""
        if not query or not query.strip():
            return []

        # Ensure collection exists before querying
        self.ensure_collection(vector_dim=384)

        # Compute dense 384-dimensional embedding
        query_vector = self.model.encode(query).tolist()

        # Query points from Qdrant
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        )

        results: List[Dict[str, Any]] = []
        for point in search_result.points:
            payload = point.payload or {}
            results.append(
                {
                    "id": point.id,
                    "score": round(float(point.score), 4) if point.score is not None else None,
                    "filepath": payload.get("filepath", ""),
                    "content": payload.get("content", ""),
                    "metadata": payload.get("metadata", {}),
                    "match_type": "dense_semantic_vector",
                }
            )
        return results


@mcp.tool()
def query_embeddings(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search the 'xeren_codebase' collection in Qdrant using dense sentence embeddings.

    Args:
        query: Natural language or semantic intent description to search for.
        limit: Number of top nearest neighbors to retrieve (default: 5).

    Returns:
        List of matching chunks with similarity score, payload, and file locations.
    """
    worker = DenseVectorWorker()
    return worker.search(query=query, limit=limit)


if __name__ == "__main__":
    mcp.run()
