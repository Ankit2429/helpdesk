"""Unit tests for Okapi BM25, HybridRetriever, and Reciprocal Rank Fusion (RRF)."""

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.bm25_store import BM25SearchStore
from campus_helpdesk.infrastructure.rag.hybrid_retriever import HybridRetriever


class MockFAISSSimilarityStore:
    """Mock dense vector store for testing RRF rank fusion."""

    def __init__(self, dense_matches: list[SearchResult]):
        self.dense_matches = dense_matches

    def search(self, query: str, limit: int) -> list[SearchResult]:
        return self.dense_matches[:limit]

    def load(self) -> None:
        pass


def test_bm25_search_store_exact_keyword_matching():
    bm25 = BM25SearchStore()
    doc1 = KnowledgeDocument(
        content="Admissions phone number: 082-2645739 for Block C inquiries.",
        metadata={"source": "admissions.md"},
    )
    doc2 = KnowledgeDocument(
        content="General campus guide for new students.",
        metadata={"source": "guide.md"},
    )
    bm25.index_documents([doc1, doc2])

    # Exact keyword query
    results = bm25.search("082-2645739", limit=5)
    assert len(results) == 1
    assert results[0].document.metadata["source"] == "admissions.md"


def test_hybrid_retriever_reciprocal_rank_fusion():
    doc_bm25 = KnowledgeDocument(
        content="Keyword match: Course code CS204 is in Block C.",
        metadata={"source": "cs204.md", "title": "CS204 Guide"},
    )
    doc_dense = KnowledgeDocument(
        content="Semantic match: Computer Science curriculum structure.",
        metadata={"source": "cs_curriculum.md", "title": "CS Curriculum"},
    )
    doc_overlap = KnowledgeDocument(
        content="Overlapping match: Computer Science CS204 lab room.",
        metadata={"source": "overlap.md", "title": "CS Lab"},
    )

    bm25_store = BM25SearchStore()
    bm25_store.index_documents([doc_bm25, doc_overlap])

    mock_faiss = MockFAISSSimilarityStore(
        dense_matches=[
            SearchResult(document=doc_dense, distance=0.2),
            SearchResult(document=doc_overlap, distance=0.4),
        ]
    )

    retriever = HybridRetriever(
        similarity_store=mock_faiss,
        bm25_store=bm25_store,
        bm25_top_k=5,
        dense_top_k=5,
        final_top_k=3,
        rrf_k=60,
    )

    fused_results, stats = retriever.search_with_stats("CS204 Computer Science")

    assert len(fused_results) <= 3
    assert stats["bm25_hits"] > 0
    assert stats["dense_hits"] > 0
    assert "retrieval_latency_ms" in stats

    # Verify overlapping doc gets boosted to rank 1 by appearing in both BM25 and FAISS
    assert fused_results[0].document.metadata["source"] == "overlap.md"


def test_hybrid_retriever_deduplication():
    identical_doc = KnowledgeDocument(
        content="Identical content in both retrievers",
        metadata={"source": "shared.md"},
    )

    bm25_store = BM25SearchStore()
    bm25_store.index_documents([identical_doc])

    mock_faiss = MockFAISSSimilarityStore(
        dense_matches=[SearchResult(document=identical_doc, distance=0.1)]
    )

    retriever = HybridRetriever(
        similarity_store=mock_faiss,
        bm25_store=bm25_store,
        final_top_k=5,
    )

    fused_results = retriever.search("Identical content")
    assert len(fused_results) == 1
