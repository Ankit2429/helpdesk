"""Ports used by the retrieval-augmented generation pipeline."""

from pathlib import Path
from typing import Protocol, Sequence

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult


class DocumentLoader(Protocol):
    """Loads a source file into framework-independent documents."""

    def load(self, source_path: Path) -> list[KnowledgeDocument]:
        """Load one supported source file."""


class DocumentChunker(Protocol):
    """Divides documents into retrieval-sized chunks."""

    def split(self, documents: Sequence[KnowledgeDocument]) -> list[KnowledgeDocument]:
        """Split source documents while preserving their metadata."""


class SimilarityStore(Protocol):
    """Stores embeddings and retrieves the nearest documents."""

    def add(self, documents: Sequence[KnowledgeDocument]) -> None:
        """Add documents to the store, creating it when necessary."""

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return the closest documents for a query."""

    def save(self) -> None:
        """Persist the current store to its configured location."""

    def load(self) -> None:
        """Load a previously persisted store."""
