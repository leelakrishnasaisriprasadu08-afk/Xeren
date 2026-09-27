"""ChromaDB backend for vector storage in Xeren RAG."""

import os
from typing import List, Optional
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

from xeren.rag.document import DocumentChunk
from xeren.rag.embeddings.base import EmbeddedChunk
from xeren.rag.retrieval.filter import MetadataFilter
from xeren.rag.retrieval.types import SearchResult
from xeren.rag.stores.base import VectorStore
from xeren.rag.stores.memory_store import InMemoryVectorStore


class ChromaVectorStore(VectorStore):
    """Vector store implementation using ChromaDB with automatic InMemory fallback."""

    def __init__(self, persist_directory: str = "data/chroma", collection_name: str = "xeren_rag"):
        self._fallback_store: Optional[InMemoryVectorStore] = None
        self.collection = None

        # On Windows or when chromadb is missing/unstable, fall back to pure-Python InMemoryVectorStore
        if os.name == "nt" or chromadb is None:
            self._fallback_store = InMemoryVectorStore()
            return

        try:
            import sys
            if "pytest" in sys.modules:
                self.client = chromadb.EphemeralClient()
                import uuid
                collection_name = f"test_{uuid.uuid4().hex}"
            else:
                os.makedirs(persist_directory, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            self.collection = self.client.get_or_create_collection(name=collection_name)
        except Exception:
            self._fallback_store = InMemoryVectorStore()

    def add_chunks(self, chunks: List[EmbeddedChunk]) -> List[str]:
        if not chunks:
            return []

        if self._fallback_store is not None:
            return self._fallback_store.add_chunks(chunks)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for embedded in chunks:
            chunk = embedded.chunk
            ids.append(chunk.chunk_id)
            embeddings.append(embedded.embedding)
            documents.append(chunk.content)
            
            # Prepare metadata (chromadb only allows str, int, float, bool)
            meta = {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "start_char_index": chunk.start_char_index if chunk.start_char_index is not None else -1,
                "end_char_index": chunk.end_char_index if chunk.end_char_index is not None else -1,
                "character_count": chunk.character_count,
                "token_count": chunk.token_count if chunk.token_count is not None else -1,
                "checksum": chunk.checksum,
                "embedding_model": embedded.embedding_model,
            }
            # flatten chunk.metadata into meta safely
            for k, v in chunk.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[f"meta_{k}"] = v
            metadatas.append(meta)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return ids

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter: Optional[MetadataFilter] = None,
    ) -> List[SearchResult]:
        if self._fallback_store is not None:
            return self._fallback_store.similarity_search(query_vector=query_vector, top_k=top_k, filter=filter)

        where_clause = None
        if filter and filter.conditions:
            where_clause = {}
            for condition in filter.conditions:
                if isinstance(condition.value, (str, int, float, bool)):
                    where_clause[f"meta_{condition.field}"] = condition.value
            if not where_clause:
                where_clause = None

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances", "embeddings"]
        )

        search_results = []
        if not results["ids"] or not results["ids"][0]:
            return []

        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            content = results["documents"][0][i]
            meta = results["metadatas"][0][i] or {}
            distance = results["distances"][0][i]
            vector = results["embeddings"][0][i] if "embeddings" in results and results["embeddings"] else None
            
            # Convert Chroma distance to similarity score
            score = 1.0 / (1.0 + distance)

            # Reconstruct chunk metadata
            chunk_metadata = {}
            for k, v in meta.items():
                if k.startswith("meta_"):
                    chunk_metadata[k[5:]] = v

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=meta.get("document_id", ""),
                content=content,
                chunk_index=meta.get("chunk_index", 0),
                total_chunks=meta.get("total_chunks", 1),
                start_char_index=meta.get("start_char_index") if meta.get("start_char_index") != -1 else None,
                end_char_index=meta.get("end_char_index") if meta.get("end_char_index") != -1 else None,
                character_count=meta.get("character_count", len(content)),
                token_count=meta.get("token_count") if meta.get("token_count") != -1 else None,
                checksum=meta.get("checksum", ""),
                metadata=chunk_metadata,
            )

            search_results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    retrieval_type="dense",
                    vector=vector
                )
            )

        return search_results

    def delete(self, chunk_ids: List[str]) -> int:
        if self._fallback_store is not None:
            return self._fallback_store.delete(chunk_ids)
        if not chunk_ids:
            return 0
        try:
            self.collection.delete(ids=chunk_ids)
            return len(chunk_ids)
        except Exception:
            return 0

    def count(self) -> int:
        if self._fallback_store is not None:
            return self._fallback_store.count()
        return self.collection.count()

    def clear(self) -> None:
        if self._fallback_store is not None:
            return self._fallback_store.clear()
        try:
            items = self.collection.get()
            if items and items["ids"]:
                self.collection.delete(ids=items["ids"])
        except Exception:
            pass
