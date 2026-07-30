"""RAG Benchmark Evaluation Metrics Module.

This module provides standard statistical and information retrieval metrics
used to quantify both retrieval quality and generated response quality in RAG systems.
All functions are side-effect free and decoupled from runtime components.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union


@dataclass
class DatasetRecord:
    """Data model representing a single evaluation record in a dataset."""

    id: Union[int, str]
    question: str
    expected_document: str
    expected_answer: str
    category: str
    expected_chunks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    difficulty: str = "medium"
    keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)


@dataclass
class EvaluationItemResult:
    """Evaluation output metrics for an individual dataset query item."""

    item_id: Union[int, str]
    question: str
    category: str
    expected_document: str
    retrieved_documents: List[str]
    expected_answer: str
    generated_answer: str
    latency_ms: float = 0.0
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    hit_rate: float = 0.0
    ndcg_at_k: float = 0.0
    exact_match: float = 0.0
    token_f1: float = 0.0
    semantic_similarity: float = 0.0
    passed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryMetrics:
    """Aggregated evaluation metrics for a specific benchmark category."""

    category: str
    total_queries: int = 0
    mean_precision_at_k: float = 0.0
    mean_recall_at_k: float = 0.0
    mean_mrr: float = 0.0
    mean_hit_rate: float = 0.0
    mean_ndcg_at_k: float = 0.0
    mean_exact_match: float = 0.0
    mean_token_f1: float = 0.0
    mean_latency_ms: float = 0.0
    pass_rate: float = 0.0


@dataclass
class AggregateBenchmarkReport:
    """Overall benchmark evaluation summary across all categories."""

    timestamp: str
    total_queries: int
    top_k: int
    overall_precision_at_k: float
    overall_recall_at_k: float
    overall_mrr: float
    overall_hit_rate: float
    overall_ndcg_at_k: float
    overall_exact_match: float
    overall_token_f1: float
    overall_mean_latency_ms: float
    overall_pass_rate: float
    category_breakdown: Dict[str, CategoryMetrics] = field(default_factory=dict)
    individual_results: List[EvaluationItemResult] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    """Lowercases text and removes punctuation/extra whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _is_doc_match(retrieved: str, expected: str) -> bool:
    """Checks if a retrieved document string matches the expected document reference."""
    if not retrieved or not expected:
        return False
    retrieved_norm = _normalize_text(retrieved)
    expected_norm = _normalize_text(expected)
    if expected_norm in retrieved_norm or retrieved_norm in expected_norm:
        return True
    return False


def precision_at_k(retrieved_docs: List[str], expected_doc: str, k: int = 5) -> float:
    """Calculates Precision@K: ratio of relevant documents in the top-K retrieved list.

    Args:
        retrieved_docs: Ordered list of retrieved document identifiers/contents.
        expected_doc: Expected document identifier or reference string.
        k: Top rank cut-off limit.

    Returns:
        Precision score between 0.0 and 1.0.
    """
    if not retrieved_docs or not expected_doc or k <= 0:
        return 0.0

    top_k_docs = retrieved_docs[:k]
    matches = sum(1 for doc in top_k_docs if _is_doc_match(doc, expected_doc))
    return matches / float(k)


def recall_at_k(
    retrieved_docs: List[str],
    expected_docs: Union[str, List[str]],
    k: int = 5,
) -> float:
    """Calculates Recall@K: proportion of relevant target documents retrieved in top-K.

    Args:
        retrieved_docs: Ordered list of retrieved document identifiers.
        expected_docs: Single target document string or list of expected documents.
        k: Top rank cut-off limit.

    Returns:
        Recall score between 0.0 and 1.0.
    """
    if not retrieved_docs or not expected_docs or k <= 0:
        return 0.0

    targets = [expected_docs] if isinstance(expected_docs, str) else expected_docs
    if not targets:
        return 0.0

    top_k_docs = retrieved_docs[:k]
    hits = sum(
        1
        for target in targets
        if any(_is_doc_match(doc, target) for doc in top_k_docs)
    )
    return hits / float(len(targets))


def mean_reciprocal_rank(retrieved_docs: List[str], expected_doc: str) -> float:
    """Calculates Reciprocal Rank (MRR element): 1/rank of the first relevant document.

    Args:
        retrieved_docs: Ordered list of retrieved document identifiers.
        expected_doc: Expected target document identifier.

    Returns:
        Reciprocal rank score (1.0 for rank 1, 0.5 for rank 2, 0.0 if not found).
    """
    if not retrieved_docs or not expected_doc:
        return 0.0

    for rank_idx, doc in enumerate(retrieved_docs, start=1):
        if _is_doc_match(doc, expected_doc):
            return 1.0 / float(rank_idx)
    return 0.0


def hit_rate_at_k(retrieved_docs: List[str], expected_doc: str, k: int = 5) -> float:
    """Calculates Hit Rate@K (1.0 if expected_doc is present in top-K, 0.0 otherwise)."""
    if not retrieved_docs or not expected_doc or k <= 0:
        return 0.0

    top_k_docs = retrieved_docs[:k]
    return 1.0 if any(_is_doc_match(doc, expected_doc) for doc in top_k_docs) else 0.0


def ndcg_at_k(retrieved_docs: List[str], expected_doc: str, k: int = 5) -> float:
    """Calculates Normalized Discounted Cumulative Gain (NDCG@K) for binary relevance.

    Args:
        retrieved_docs: Ordered list of retrieved document identifiers.
        expected_doc: Target document identifier.
        k: Top rank cut-off limit.

    Returns:
        NDCG score between 0.0 and 1.0.
    """
    if not retrieved_docs or not expected_doc or k <= 0:
        return 0.0

    dcg = 0.0
    for rank_idx, doc in enumerate(retrieved_docs[:k], start=1):
        rel = 1.0 if _is_doc_match(doc, expected_doc) else 0.0
        dcg += rel / math.log2(rank_idx + 1)

    # Ideal DCG for single target document is at rank 1: rel=1.0 / log2(2) = 1.0
    idcg = 1.0
    return dcg / idcg


def exact_match_score(predicted: str, expected: str) -> float:
    """Computes exact match score (1.0 if normalized strings match, 0.0 otherwise)."""
    pred_norm = _normalize_text(predicted)
    exp_norm = _normalize_text(expected)
    if not pred_norm and not exp_norm:
        return 1.0
    return 1.0 if pred_norm == exp_norm else 0.0


def token_f1_score(predicted: str, expected: str) -> float:
    """Computes token-level precision, recall, and F1 score between predicted and expected text."""
    pred_tokens = _normalize_text(predicted).split()
    exp_tokens = _normalize_text(expected).split()

    if not pred_tokens and not exp_tokens:
        return 1.0
    if not pred_tokens or not exp_tokens:
        return 0.0

    common_tokens = set(pred_tokens) & set(exp_tokens)
    num_same = sum(min(pred_tokens.count(w), exp_tokens.count(w)) for w in common_tokens)

    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(exp_tokens)
    return (2.0 * precision * recall) / (precision + recall)
