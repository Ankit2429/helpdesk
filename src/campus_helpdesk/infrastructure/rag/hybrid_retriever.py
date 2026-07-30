"""Hybrid Retrieval Engine using Reciprocal Rank Fusion (RRF) of BM25 + FAISS Dense Search."""

import hashlib
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from campus_helpdesk.application.exceptions import RetrievalError
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.bm25_store import BM25SearchStore
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines BM25 sparse keyword search and FAISS dense vector search via Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        similarity_store: FAISSSimilarityStore,
        bm25_store: BM25SearchStore | None = None,
        bm25_top_k: int = 25,
        dense_top_k: int = 25,
        final_top_k: int = 25,
        rrf_k: int = 60,
        weight_dense: float = 0.5,
        weight_sparse: float = 0.5,
        fusion_mode: str = "weighted_hybrid",
    ) -> None:
        self.similarity_store = similarity_store
        self.bm25_store = bm25_store or BM25SearchStore()
        self.bm25_top_k = bm25_top_k
        self.dense_top_k = dense_top_k
        self.final_top_k = final_top_k
        self.rrf_k = rrf_k
        self.weight_dense = weight_dense
        self.weight_sparse = weight_sparse
        self.fusion_mode = fusion_mode
        self._bm25_indexed = len(self.bm25_store._documents) > 0

    @property
    def _embedding_metadata(self) -> dict[str, Any]:
        """Forward embedding metadata from underlying FAISS store."""
        return getattr(self.similarity_store, "_embedding_metadata", {})

    @property
    def _index_path(self) -> Any:
        """Forward index path from underlying FAISS store."""
        return getattr(self.similarity_store, "_index_path", Path("data/faiss"))

    def reset(self) -> None:
        """Reset FAISS vector store and BM25 index."""
        if hasattr(self.similarity_store, "reset"):
            self.similarity_store.reset()
        self.bm25_store = BM25SearchStore()
        self._bm25_indexed = False

    def index_bm25(self, documents: Sequence[KnowledgeDocument]) -> None:
        """Populate BM25 keyword index from canonical KnowledgeDocument chunks."""
        self.bm25_store.index_documents(documents)
        self._bm25_indexed = True
        logger.info("BM25 index populated with %d document chunks.", len(documents))

    def add(self, documents: Sequence[KnowledgeDocument]) -> None:
        """Add documents to FAISS vector store and update BM25 keyword index."""
        self.similarity_store.add(documents)
        self.index_bm25(documents)

    def save(self) -> None:
        """Persist FAISS vector store to disk."""
        self.similarity_store.save()

    def load(self) -> None:
        """Load FAISS vector store and reconstruct BM25 keyword index if store is initialized."""
        self.similarity_store.load()
        if hasattr(self.similarity_store, "_store") and self.similarity_store._store is not None:
            # Reconstruct KnowledgeDocuments from loaded FAISS docstore for BM25 keyword index
            try:
                langchain_docs = list(self.similarity_store._store.docstore._dict.values())
                k_docs = [
                    KnowledgeDocument(
                        content=d.page_content,
                        metadata={str(k): str(v) for k, v in d.metadata.items()},
                    )
                    for d in langchain_docs
                ]
                self.index_bm25(k_docs)
            except Exception as err:
                logger.warning("Could not automatically populate BM25 index from loaded FAISS store: %s", err)

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        """Perform hybrid search using Reciprocal Rank Fusion of BM25 and FAISS dense search."""
        fused_results, _ = self.search_with_stats(query, limit=limit)
        return fused_results

    def search_with_stats(
        self, query: str, limit: int | None = None
    ) -> tuple[list[SearchResult], dict[str, Any]]:
        """Perform hybrid search and return fused results alongside diagnostic performance statistics."""
        start_time = time.perf_counter()
        target_limit = limit if limit is not None else self.final_top_k

        # Direct shortcuts for dense_only and bm25_only fusion modes
        if self.fusion_mode == "dense_only":
            dense_results = self.similarity_store.search(query, limit=target_limit)
            return dense_results[:target_limit], {"fusion_mode": "dense_only"}
        elif self.fusion_mode == "bm25_only" and self._bm25_indexed:
            bm25_results = self.bm25_store.search(query, limit=target_limit)
            return bm25_results[:target_limit], {"fusion_mode": "bm25_only"}

        # 1. BM25 Sparse Search
        bm25_results: list[SearchResult] = []
        if self._bm25_indexed and self.weight_sparse > 0:
            try:
                bm25_results = self.bm25_store.search(query, limit=self.bm25_top_k)
            except Exception as err:
                logger.warning("BM25 search error: %s", err)

        # 2. FAISS Dense Search
        dense_results: list[SearchResult] = []
        if self.weight_dense > 0:
            try:
                dense_results = self.similarity_store.search(query, limit=self.dense_top_k)
            except RetrievalError as err:
                logger.error("FAISS dense search RetrievalError: %s", err)
                raise
            except Exception as err:
                logger.warning("FAISS dense search unexpected error: %s", err)

        # 3. Reciprocal Rank Fusion (Weighted RRF)
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, KnowledgeDocument] = {}
        distance_map: dict[str, float] = {}

        # Process BM25 ranks
        for rank, match in enumerate(bm25_results, start=1):
            doc = match.document
            doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
            rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + self.weight_sparse * (1.0 / (self.rrf_k + rank))
            doc_map[doc_hash] = doc
            distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

        # Process FAISS dense ranks
        for rank, match in enumerate(dense_results, start=1):
            doc = match.document
            doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
            rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + self.weight_dense * (1.0 / (self.rrf_k + rank))
            doc_map[doc_hash] = doc
            distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

        # Sort documents by descending RRF score
        sorted_hashes = sorted(rrf_scores.keys(), key=lambda h: rrf_scores[h], reverse=True)
        top_hashes = sorted_hashes[:target_limit]

        fused_results = [
            SearchResult(
                document=doc_map[h],
                distance=distance_map[h],
            )
            for h in top_hashes
        ]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        stats = {
            "query": query,
            "bm25_hits": len(bm25_results),
            "dense_hits": len(dense_results),
            "fused_results_count": len(fused_results),
            "retrieval_latency_ms": duration_ms,
            "fused_ranking": [
                {
                    "rank": idx + 1,
                    "rrf_score": round(rrf_scores[h], 5),
                    "source": doc_map[h].metadata.get("source", "unknown"),
                    "snippet": doc_map[h].content[:100].replace("\n", " "),
                }
                for idx, h in enumerate(top_hashes)
            ],
        }

        # If both sources failed to provide results, raise a RetrievalError
        if not fused_results:
            logger.error("Hybrid retrieval produced no results; both BM25 and FAISS may have failed.")
            raise RetrievalError("Hybrid retrieval failed to return any results.")

        return fused_results, stats
