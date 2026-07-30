"""Retrieval Layer Package.

Provides vector database query execution, reciprocal rank fusion hybrid search,
cross-encoder re-ranking, and citation formatting.
"""

from retrieval.citation_formatter import CitationFormatter
from retrieval.reranker import CrossEncoderReranker
from retrieval.retriever import ChromaRetriever

__all__ = [
    "ChromaRetriever",
    "CrossEncoderReranker",
    "CitationFormatter",
]
