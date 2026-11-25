"""Ingestion pipeline orchestrating document loading, normalization, chunking, and vector indexing."""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from xeren.rag.chunkers.base import BaseChunker
from xeren.rag.chunkers.recursive import RecursiveTextChunker
from xeren.rag.document import Document, DocumentChunk
from xeren.rag.embeddings.base import BaseEmbeddingModel
from xeren.rag.errors import PipelineExecutionError
from xeren.rag.loaders.directory import DirectoryLoader
from xeren.rag.loaders.registry import LoaderRegistry
from xeren.rag.normalizers.base import BaseNormalizer
from xeren.rag.normalizers.text_normalizer import TextNormalizer
from xeren.rag.stores.base import VectorStore

if TYPE_CHECKING:
    from xeren.rag.retrieval.keyword import KeywordRetriever

logger = logging.getLogger("xeren.rag.pipeline")


class IngestionPipeline:
    """End-to-end document ingestion and indexing pipeline for RAG."""

    def __init__(
        self,
        loader_registry: Optional[LoaderRegistry] = None,
        normalizer: Optional[BaseNormalizer] = None,
        chunker: Optional[BaseChunker] = None,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
        keyword_retriever: Optional["KeywordRetriever"] = None,
    ) -> None:
        self.loader_registry = loader_registry or LoaderRegistry()
        self.normalizer = normalizer or TextNormalizer()
        self.chunker = chunker or RecursiveTextChunker()
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.keyword_retriever = keyword_retriever

    def process_document(self, document: Document) -> List[DocumentChunk]:
        """Normalize a single Document and split it into DocumentChunks."""
        try:
            normalized_doc = self.normalizer.normalize(document)
            chunks = self.chunker.chunk(normalized_doc)
            logger.debug(
                "Processed document into chunks",
                extra={"document_id": document.id, "chunks_count": len(chunks)},
            )
            return chunks
        except Exception as err:
            logger.error("Failed processing document %s: %s", document.id, err)
            raise PipelineExecutionError(
                f"Failed to process document {document.id}: {err}", raw_error=err
            ) from err

    def process_documents(self, documents: List[Document]) -> List[DocumentChunk]:
        """Process a collection of Document objects."""
        all_chunks: List[DocumentChunk] = []
        for doc in documents:
            all_chunks.extend(self.process_document(doc))
        return all_chunks

    def process_text(
        self,
        text: str,
        source: str = "in_memory",
        title: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Ingest raw text into chunks."""
        doc = Document.from_text(text=text, source=source, title=title, extra=extra)
        return self.process_document(doc)

    async def aprocess_text(
        self,
        text: str,
        source: str = "in_memory",
        title: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Asynchronously ingest raw text into chunks."""
        return await asyncio.to_thread(self.process_text, text, source, title, extra)

    def process_file(self, file_path: Union[str, Path]) -> List[DocumentChunk]:
        """Load, normalize, and chunk a single file."""
        path = Path(file_path)
        loader = self.loader_registry.get_loader_for(path)
        docs = loader.load(path)
        return self.process_documents(docs)

    async def aprocess_file(self, file_path: Union[str, Path]) -> List[DocumentChunk]:
        """Asynchronously load, normalize, and chunk a single file."""
        return await asyncio.to_thread(self.process_file, file_path)

    def process_directory(
        self,
        dir_path: Union[str, Path],
        recursive: bool = True,
        glob_pattern: str = "**/*",
    ) -> List[DocumentChunk]:
        """Recursively scan a directory, ingest all supported files, and produce chunks."""
        dir_loader = DirectoryLoader(
            registry=self.loader_registry,
            glob_pattern=glob_pattern,
            recursive=recursive,
        )
        docs = dir_loader.load(dir_path)
        return self.process_documents(docs)

    async def aprocess_directory(
        self,
        dir_path: Union[str, Path],
        recursive: bool = True,
        glob_pattern: str = "**/*",
    ) -> List[DocumentChunk]:
        """Asynchronously process an entire directory."""
        return await asyncio.to_thread(self.process_directory, dir_path, recursive, glob_pattern)

    def index_chunks(
        self,
        chunks: List[DocumentChunk],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Embed chunks and insert them into the vector store. Returns list of inserted chunk IDs."""
        embedder = embedding_model or self.embedding_model
        store = vector_store or self.vector_store

        if not embedder:
            raise PipelineExecutionError("Cannot index chunks: No embedding model configured.")
        if not store:
            raise PipelineExecutionError("Cannot index chunks: No vector store configured.")

        if not chunks:
            return []

        try:
            embedded_chunks = embedder.embed_chunks(chunks)
            inserted_ids = store.add_chunks(embedded_chunks)
            if self.keyword_retriever is not None:
                self.keyword_retriever.add_chunks(chunks)
            logger.info(
                "Indexed chunks into vector store",
                extra={"chunks_count": len(chunks), "inserted_ids": inserted_ids},
            )
            return inserted_ids
        except Exception as err:
            logger.error("Failed indexing chunks: %s", err)
            raise PipelineExecutionError(f"Failed indexing chunks: {err}", raw_error=err) from err

    async def aindex_chunks(
        self,
        chunks: List[DocumentChunk],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously embed chunks and insert them into the vector store."""
        embedder = embedding_model or self.embedding_model
        store = vector_store or self.vector_store

        if not embedder:
            raise PipelineExecutionError("Cannot index chunks: No embedding model configured.")
        if not store:
            raise PipelineExecutionError("Cannot index chunks: No vector store configured.")

        if not chunks:
            return []

        try:
            embedded_chunks = await embedder.aembed_chunks(chunks)
            inserted_ids = await store.aadd_chunks(embedded_chunks)
            if self.keyword_retriever is not None:
                self.keyword_retriever.add_chunks(chunks)
            return inserted_ids
        except Exception as err:
            logger.error("Failed async indexing chunks: %s", err)
            raise PipelineExecutionError(f"Failed async indexing chunks: {err}", raw_error=err) from err

    def index_document(
        self,
        document: Document,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Process a Document into chunks, embed, and index into the vector store."""
        chunks = self.process_document(document)
        return self.index_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    async def aindex_document(
        self,
        document: Document,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously process a Document into chunks, embed, and index into the vector store."""
        chunks = self.process_document(document)
        return await self.aindex_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    def index_documents(
        self,
        documents: List[Document],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Process multiple Documents into chunks, embed, and index into the vector store."""
        chunks = self.process_documents(documents)
        return self.index_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    async def aindex_documents(
        self,
        documents: List[Document],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously process multiple Documents into chunks, embed, and index into the vector store."""
        chunks = self.process_documents(documents)
        return await self.aindex_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    def index_text(
        self,
        text: str,
        source: str = "in_memory",
        title: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Ingest raw text, chunk, embed, and index into the vector store."""
        chunks = self.process_text(text, source=source, title=title, extra=extra)
        return self.index_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    async def aindex_text(
        self,
        text: str,
        source: str = "in_memory",
        title: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously ingest raw text, chunk, embed, and index into the vector store."""
        chunks = await self.aprocess_text(text, source=source, title=title, extra=extra)
        return await self.aindex_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    def index_file(
        self,
        file_path: Union[str, Path],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Load a file, normalize, chunk, embed, and index into the vector store."""
        chunks = self.process_file(file_path)
        return self.index_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    async def aindex_file(
        self,
        file_path: Union[str, Path],
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously load a file, normalize, chunk, embed, and index into the vector store."""
        chunks = await self.aprocess_file(file_path)
        return await self.aindex_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    def index_directory(
        self,
        dir_path: Union[str, Path],
        recursive: bool = True,
        glob_pattern: str = "**/*",
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Scan a directory, load and chunk all files, embed, and index into the vector store."""
        chunks = self.process_directory(dir_path, recursive=recursive, glob_pattern=glob_pattern)
        return self.index_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)

    async def aindex_directory(
        self,
        dir_path: Union[str, Path],
        recursive: bool = True,
        glob_pattern: str = "**/*",
        embedding_model: Optional[BaseEmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> List[str]:
        """Asynchronously scan a directory, chunk all files, embed, and index into the vector store."""
        chunks = await self.aprocess_directory(dir_path, recursive=recursive, glob_pattern=glob_pattern)
        return await self.aindex_chunks(chunks, embedding_model=embedding_model, vector_store=vector_store)
