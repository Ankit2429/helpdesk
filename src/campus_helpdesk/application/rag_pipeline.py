"""Reusable orchestration for local knowledge ingestion and retrieval."""

import logging
from pathlib import Path

from campus_helpdesk.application.knowledge_ports import (
    DocumentChunker,
    DocumentLoader,
    SimilarityStore,
)
from campus_helpdesk.domain.knowledge import IngestionResult, SearchResult

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Coordinates document loading, chunking, indexing, and similarity search."""

    def __init__(
        self,
        document_loader: DocumentLoader,
        document_chunker: DocumentChunker,
        similarity_store: SimilarityStore,
        search_limit: int,
    ) -> None:
        self._document_loader = document_loader
        self._document_chunker = document_chunker
        self._similarity_store = similarity_store
        self._search_limit = search_limit

    def ingest_pdf(self, source_path: Path, persist: bool = True) -> IngestionResult:
        """Load, chunk, index, and optionally persist a PDF source file."""
        documents = self._document_loader.load(source_path)
        chunks = self._document_chunker.split(documents)
        if not chunks:
            raise ValueError("The source file did not produce any indexable text chunks.")

        self._similarity_store.add(chunks)
        if persist:
            self._similarity_store.save()

        result = IngestionResult(
            source_path=str(source_path),
            document_count=len(documents),
            chunk_count=len(chunks),
        )
        logger.info(
            "Knowledge source ingested",
            extra={"document_count": result.document_count, "chunk_count": result.chunk_count},
        )
        return result

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        """Find relevant indexed chunks for a natural-language query."""
        if not query.strip():
            raise ValueError("Search query cannot be blank.")

        result_limit = limit if limit is not None else self._search_limit
        if result_limit < 1:
            raise ValueError("Search limit must be at least one.")

        return self._similarity_store.search(query, result_limit)

    def load_index(self) -> None:
        """Restore a previously persisted similarity index."""
        self._similarity_store.load()
