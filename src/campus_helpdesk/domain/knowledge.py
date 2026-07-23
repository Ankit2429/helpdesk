"""Framework-independent knowledge entities."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """A source document or chunk that can be stored and retrieved."""

    content: str
    metadata: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A knowledge document returned by vector search with its FAISS distance."""

    document: KnowledgeDocument
    distance: float


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Counts produced while adding a source file to the knowledge base."""

    source_path: str
    document_count: int
    chunk_count: int
