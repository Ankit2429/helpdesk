"""Retrieval Evaluation Metrics Data Models and Calculation Utilities.

This module provides data models for individual retrieval evaluation items,
category metric summaries, aggregate benchmarking reports, and statistical calculations
(Recall@1/3/5, MRR, Mean/Median/P95 Latency, Success/Failure rates).
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class RetrievedDocItem:
    """Represents a single document retrieved by the RAG search engine."""

    doc_name: str
    score: float
    rank: int


@dataclass
class RetrievalItemResult:
    """Retrieval evaluation results for an individual question item."""

    item_id: Union[int, str]
    question: str
    expected_document: str
    category: str
    difficulty: str
    perspective: str
    top1_retrieved: Optional[str] = None
    top3_retrieved: List[str] = field(default_factory=list)
    top5_retrieved: List[str] = field(default_factory=list)
    retrieved_scores: List[float] = field(default_factory=list)
    retrieval_rank: int = 0  # 1-indexed rank of expected document, or 0 if not in top K
    top1_match: bool = False
    top3_match: bool = False
    top5_match: bool = False
    reciprocal_rank: float = 0.0
    latency_ms: float = 0.0
    failure_reason: Optional[str] = None


@dataclass
class FailedCaseRecord:
    """Detailed record of a failed retrieval item for error diagnosis."""

    item_id: Union[int, str]
    question: str
    expected_document: str
    category: str
    difficulty: str
    perspective: str
    retrieved_documents: List[str]
    similarity_scores: List[float]
    retrieval_rank: int
    failure_reason: str


@dataclass
class RetrievalCategoryMetrics:
    """Aggregated retrieval evaluation metrics for a single domain category."""

    category: str
    total_queries: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0
    mean_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0


@dataclass
class RetrievalAggregateReport:
    """Overall benchmark evaluation report across all categories."""

    timestamp: str
    total_queries: int
    overall_success_count: int
    overall_failure_count: int
    overall_success_rate: float
    overall_failure_rate: float
    overall_recall_at_1: float
    overall_recall_at_3: float
    overall_recall_at_5: float
    overall_mrr: float
    overall_mean_latency_ms: float
    overall_median_latency_ms: float
    overall_p95_latency_ms: float
    category_breakdown: Dict[str, RetrievalCategoryMetrics] = field(default_factory=dict)
    item_results: List[RetrievalItemResult] = field(default_factory=list)
    failed_cases: List[FailedCaseRecord] = field(default_factory=list)


def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculates a specific percentile value from a list of numbers."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    k = (n - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def compute_category_metrics(
    category_name: str, items: List[RetrievalItemResult]
) -> RetrievalCategoryMetrics:
    """Computes category metrics from a list of RetrievalItemResult items."""
    total = len(items)
    if total == 0:
        return RetrievalCategoryMetrics(category=category_name)

    top1_matches = sum(1 for x in items if x.top1_match)
    top3_matches = sum(1 for x in items if x.top3_match)
    top5_matches = sum(1 for x in items if x.top5_match)
    successes = top5_matches
    failures = total - successes

    mrr_sum = sum(x.reciprocal_rank for x in items)
    latencies = [x.latency_ms for x in items]

    mean_lat = statistics.mean(latencies) if latencies else 0.0
    median_lat = statistics.median(latencies) if latencies else 0.0
    p95_lat = calculate_percentile(latencies, 95.0)

    return RetrievalCategoryMetrics(
        category=category_name,
        total_queries=total,
        success_count=successes,
        failure_count=failures,
        success_rate=successes / float(total),
        failure_rate=failures / float(total),
        recall_at_1=top1_matches / float(total),
        recall_at_3=top3_matches / float(total),
        recall_at_5=top5_matches / float(total),
        mrr=mrr_sum / float(total),
        mean_latency_ms=mean_lat,
        median_latency_ms=median_lat,
        p95_latency_ms=p95_lat,
    )
