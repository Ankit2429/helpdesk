"""Hybrid Search Engine with Reciprocal Rank Fusion (RRF).

Combines Sparse BM25 Keyword Search (rank_bm25) with Dense Vector Search (ChromaDB)
using Reciprocal Rank Fusion (RRF) scoring:
    RRF_Score(d) = 1 / (60 + rank_dense) + 1 / (60 + rank_bm25)
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from logger.logger import get_logger

logger = get_logger("hybrid_search")


@dataclass
class HybridSearchResult:
    """Dataclass holding candidate item with dense rank, BM25 rank, and merged RRF score."""

    doc_id: str
    text: str
    metadata: Dict[str, Any]
    dense_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    dense_rank: int = 999
    bm25_rank: int = 999


class HybridSearchEngine:
    """Combines BM25Okapi sparse retrieval with ChromaDB dense vector search using RRF."""

    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k
        self.bm25_model: Optional[BM25Okapi] = None
        self.corpus_records: List[Dict[str, Any]] = []
        self.doc_id_to_index: Dict[str, int] = {}

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple lower-case word tokenization for BM25."""
        return text.lower().split()

    def build_bm25_index(self, records: List[Dict[str, Any]]) -> None:
        """Build BM25 search index from dataset records containing 'text' and 'metadata'."""
        self.corpus_records = records
        self.doc_id_to_index = {}
        tokenized_corpus: List[List[str]] = []

        for idx, rec in enumerate(records):
            doc_id = rec.get("metadata", {}).get("id") or f"doc_{idx}"
            self.doc_id_to_index[doc_id] = idx
            tokenized_corpus.append(self.tokenize(rec.get("text", "")))

        logger.info(f"Building BM25Okapi index over {len(tokenized_corpus)} corpus documents.")
        self.bm25_model = BM25Okapi(tokenized_corpus)

    def bm25_search(self, query: str, top_k: int = 20) -> List[Tuple[Dict[str, Any], float]]:
        """Search BM25 index returning top_k records and BM25 raw scores."""
        if not self.bm25_model or not self.corpus_records:
            return []

        tokenized_query = self.tokenize(query)
        scores = self.bm25_model.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0:
                results.append((self.corpus_records[idx], score))
        return results

    def fuse_rrf(
        self,
        dense_results: List[Dict[str, Any]],
        bm25_results: List[Tuple[Dict[str, Any], float]],
        top_k: int = 20,
    ) -> List[HybridSearchResult]:
        """Merge dense vector and BM25 search candidates using Reciprocal Rank Fusion (RRF)."""
        candidates: Dict[str, HybridSearchResult] = {}

        # 1. Process Dense Results
        for rank, dense_item in enumerate(dense_results, start=1):
            meta = dense_item.get("metadata", {})
            doc_id = meta.get("id") or meta.get("chunk_id", f"dense_{rank}")
            text = dense_item.get("text", "")
            score = dense_item.get("score", 0.0)

            candidates[doc_id] = HybridSearchResult(
                doc_id=doc_id,
                text=text,
                metadata=meta,
                dense_score=score,
                dense_rank=rank,
            )

        # 2. Process BM25 Results
        for rank, (bm25_rec, bm25_score) in enumerate(bm25_results, start=1):
            meta = bm25_rec.get("metadata", {})
            doc_id = meta.get("id") or meta.get("chunk_id", f"bm25_{rank}")
            text = bm25_rec.get("text", "")

            if doc_id in candidates:
                candidates[doc_id].bm25_rank = rank
                candidates[doc_id].bm25_score = bm25_score
            else:
                candidates[doc_id] = HybridSearchResult(
                    doc_id=doc_id,
                    text=text,
                    metadata=meta,
                    bm25_score=bm25_score,
                    bm25_rank=rank,
                )

        # 3. Calculate RRF Scores
        fused_list: List[HybridSearchResult] = []
        for cand in candidates.values():
            rrf_dense = 1.0 / (self.rrf_k + cand.dense_rank) if cand.dense_rank != 999 else 0.0
            rrf_bm25 = 1.0 / (self.rrf_k + cand.bm25_rank) if cand.bm25_rank != 999 else 0.0
            cand.rrf_score = round(rrf_dense + rrf_bm25, 6)
            fused_list.append(cand)

        # Sort descending by RRF score
        fused_list.sort(key=lambda x: x.rrf_score, reverse=True)
        logger.info(f"Merged {len(dense_results)} dense and {len(bm25_results)} BM25 results into {len(fused_list)} RRF candidates.")
        return fused_list[:top_k]
