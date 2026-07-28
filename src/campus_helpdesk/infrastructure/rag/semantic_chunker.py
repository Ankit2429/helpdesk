"""Pluggable composite chunker with Markdown semantic chunking support."""

from collections.abc import Sequence
from typing import Any

from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.markdown_chunker import MarkdownSemanticChunker
from campus_helpdesk.infrastructure.rag.text_chunker import RecursiveTextChunker


class SemanticDocumentChunker:
    """Composite document chunker routing Markdown to MarkdownSemanticChunker and PDF to RecursiveTextChunker."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Sequence[str] = ("\n\n", "\n", " ", ""),
        add_start_index: bool = False,
    ) -> None:
        self._markdown_chunker = MarkdownSemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._recursive_chunker = RecursiveTextChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            add_start_index=add_start_index,
        )

    def split(self, documents: Sequence[KnowledgeDocument]) -> list[KnowledgeDocument]:
        """Split documents using format-aware semantic strategies."""
        all_chunks: list[KnowledgeDocument] = []
        for document in documents:
            source = str(document.metadata.get("source", "")).casefold()
            if source.endswith(".md") or "#" in document.content[:200]:
                chunks = self._markdown_chunker.split_document(document)
            else:
                chunks = self._recursive_chunker.split([document])
            all_chunks.extend(chunks)
        return all_chunks


def compute_chunk_statistics(chunks: Sequence[KnowledgeDocument]) -> dict[str, Any]:
    """Compute structural statistics for a list of generated KnowledgeDocument chunks."""
    if not chunks:
        return {
            "number_of_chunks": 0,
            "average_chunk_size": 0.0,
            "largest_chunk_size": 0,
            "smallest_chunk_size": 0,
        }

    sizes = [len(c.content) for c in chunks]
    return {
        "number_of_chunks": len(chunks),
        "average_chunk_size": round(sum(sizes) / len(sizes), 2),
        "largest_chunk_size": max(sizes),
        "smallest_chunk_size": min(sizes),
    }
