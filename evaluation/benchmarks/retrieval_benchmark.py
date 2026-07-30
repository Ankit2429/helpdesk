"""Retrieval Benchmarking Engine Module.

Executes query benchmarking against the existing RAG retriever, compares top-K retrieved
documents with expected target documents, computes Recall@1/3/5 & MRR, parallelizes evaluation,
and collects failure analysis records.
"""

import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Ensure src/ package root is in sys.path
_src_dir = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from evaluation.benchmarks.retrieval_metrics import (
    FailedCaseRecord,
    RetrievalAggregateReport,
    RetrievalCategoryMetrics,
    RetrievalItemResult,
    RetrievedDocItem,
    calculate_percentile,
    compute_category_metrics,
)

logger = logging.getLogger(__name__)

# Type alias for retriever search callable:
# query: str, top_k: int -> List[RetrievedDocItem]
RetrieverCallable = Callable[[str, int], List[RetrievedDocItem]]


def _normalize_doc_name(doc_name: str) -> str:
    """Normalizes document filename or path for exact match comparison."""
    if not doc_name:
        return ""
    name = Path(doc_name).name.lower().strip()
    return name if name.endswith(".md") else f"{name}.md"


def _is_doc_match(retrieved: str, expected: str) -> bool:
    """Determines if a retrieved document string matches the expected document reference."""
    if not retrieved or not expected:
        return False
    ret_norm = _normalize_doc_name(retrieved)
    exp_norm = _normalize_doc_name(expected)
    return ret_norm == exp_norm or ret_norm.replace(".md", "") == exp_norm.replace(".md", "")


class RetrievalBenchmark:
    """Core evaluation engine for RAG retriever benchmarking."""

    def __init__(
        self,
        dataset_dir: Union[str, Path] = "evaluation/datasets",
        top_k: int = 5,
        max_workers: int = 4,
        retriever_pipeline: Optional[RetrieverCallable] = None,
    ):
        """Initializes retrieval benchmark engine."""
        self.dataset_dir = Path(dataset_dir)
        self.top_k = top_k
        self.max_workers = max_workers
        self.retriever = retriever_pipeline or self._init_system_retriever()

    def _init_system_retriever(self) -> RetrieverCallable:
        """Attempts to wire into the system RAG retriever."""
        try:
            from campus_helpdesk.config.settings import Settings
            from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

            settings = Settings(faiss_allow_dangerous_deserialization=True)
            pipeline = create_rag_pipeline(settings)

            def system_search(query: str, k: int) -> List[RetrievedDocItem]:
                results = pipeline.search(query, limit=k)
                items = []
                for idx, res in enumerate(results, start=1):
                    doc = getattr(res, "document", None)
                    metadata = getattr(doc, "metadata", {}) if doc else {}
                    doc_name = (
                        metadata.get("source_filename")
                        or metadata.get("source")
                        or getattr(res, "source", None)
                        or str(res)
                    )
                    score = float(getattr(res, "distance", 1.0 / idx))
                    items.append(RetrievedDocItem(doc_name=doc_name, score=score, rank=idx))
                return items

            logger.info("Successfully connected to system RAG retriever.")
            return system_search

        except Exception as e:
            logger.error(f"System retriever connection failed: {e}")
            return self._mock_retriever_adapter

    def _mock_retriever_adapter(self, query: str, k: int) -> List[RetrievedDocItem]:
        """Mock retriever adapter for standalone testing and dry-run execution."""
        # Simulated fast search response
        items = []
        for idx in range(1, k + 1):
            items.append(
                RetrievedDocItem(
                    doc_name=f"simulated_document_{idx}.md",
                    score=round(1.0 - (idx * 0.15), 4),
                    rank=idx,
                )
            )
        return items

    def load_dataset_records(self, file_path: Path) -> List[Dict[str, Any]]:
        """Loads dataset records from a single JSON file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading dataset {file_path}: {e}")
            return []

    def evaluate_item(self, item_dict: Dict[str, Any]) -> RetrievalItemResult:
        """Evaluates retrieval performance for a single dataset query record.

        Args:
            item_dict: Raw item dictionary loaded from dataset JSON.

        Returns:
            RetrievalItemResult object.
        """
        item_id = item_dict.get("id", 0)
        question = item_dict.get("question", "")
        expected_doc = item_dict.get("expected_document", "")
        category = item_dict.get("category", "Misc")
        difficulty = item_dict.get("difficulty", "medium")
        perspective = item_dict.get("perspective", "visitor")

        start_time = time.perf_counter()
        try:
            retrieved_items = self.retriever(question, self.top_k)
        except Exception as e:
            logger.error(f"Retriever exception for item ID {item_id}: {e}")
            retrieved_items = []
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        top_docs = [it.doc_name for it in retrieved_items]
        top_scores = [it.score for it in retrieved_items]

        top1_retrieved = top_docs[0] if top_docs else None
        top3_retrieved = top_docs[:3]
        top5_retrieved = top_docs[:5]

        # Calculate rank and match indicators
        rank = 0
        for idx, doc_name in enumerate(top_docs, start=1):
            if _is_doc_match(doc_name, expected_doc):
                rank = idx
                break

        top1_match = (rank == 1)
        top3_match = (1 <= rank <= 3)
        top5_match = (1 <= rank <= 5)
        reciprocal_rank = (1.0 / float(rank)) if rank > 0 else 0.0

        failure_reason = None
        if not top5_match:
            if not top_docs:
                failure_reason = "Zero search results returned"
            else:
                failure_reason = f"Expected document '{expected_doc}' not found in top 5 retrieved results"
        elif not top1_match:
            failure_reason = f"Ranked at position #{rank} instead of Top 1"

        return RetrievalItemResult(
            item_id=item_id,
            question=question,
            expected_document=expected_doc,
            category=category,
            difficulty=difficulty,
            perspective=perspective,
            top1_retrieved=top1_retrieved,
            top3_retrieved=top3_retrieved,
            top5_retrieved=top5_retrieved,
            retrieved_scores=top_scores,
            retrieval_rank=rank,
            top1_match=top1_match,
            top3_match=top3_match,
            top5_match=top5_match,
            reciprocal_rank=reciprocal_rank,
            latency_ms=latency_ms,
            failure_reason=failure_reason,
        )

    def run_benchmark(
        self,
        category_filter: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> RetrievalAggregateReport:
        """Executes the full retrieval benchmark suite across dataset categories.

        Args:
            category_filter: Optional domain category filter.
            progress_callback: Optional progress callback function(current, total, current_item_desc).

        Returns:
            RetrievalAggregateReport summarizing metrics and failure cases.
        """
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        json_files = sorted(list(self.dataset_dir.glob("*.json")))

        all_items_to_eval: List[Dict[str, Any]] = []

        for json_file in json_files:
            file_category = json_file.stem.capitalize()
            if category_filter and file_category.lower() != category_filter.lower() and json_file.stem.lower() != category_filter.lower():
                continue

            records = self.load_dataset_records(json_file)
            for r in records:
                if "category" not in r:
                    r["category"] = file_category
            all_items_to_eval.extend(records)

        total_queries = len(all_items_to_eval)
        logger.info(f"Total evaluation query items to benchmark: {total_queries}")

        if total_queries == 0:
            logger.warning("No records found to benchmark.")
            return RetrievalAggregateReport(
                timestamp=timestamp,
                total_queries=0,
                overall_success_count=0,
                overall_failure_count=0,
                overall_success_rate=0.0,
                overall_failure_rate=0.0,
                overall_recall_at_1=0.0,
                overall_recall_at_3=0.0,
                overall_recall_at_5=0.0,
                overall_mrr=0.0,
                overall_mean_latency_ms=0.0,
                overall_median_latency_ms=0.0,
                overall_p95_latency_ms=0.0,
            )

        evaluated_results: List[RetrievalItemResult] = []

        # Execute evaluation (parallelized via ThreadPoolExecutor)
        if self.max_workers > 1 and total_queries > 10:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {
                    executor.submit(self.evaluate_item, item): idx
                    for idx, item in enumerate(all_items_to_eval, start=1)
                }
                completed_count = 0
                for future in as_completed(future_map):
                    completed_count += 1
                    res = future.result()
                    evaluated_results.append(res)
                    if progress_callback:
                        progress_callback(completed_count, total_queries, f"[{res.category}] {res.question[:30]}...")
        else:
            for idx, item in enumerate(all_items_to_eval, start=1):
                res = self.evaluate_item(item)
                evaluated_results.append(res)
                if progress_callback:
                    progress_callback(idx, total_queries, f"[{res.category}] {res.question[:30]}...")

        # Group by category and compute category metrics
        category_map: Dict[str, List[RetrievalItemResult]] = {}
        failed_cases: List[FailedCaseRecord] = []

        for item_res in evaluated_results:
            category_map.setdefault(item_res.category, []).append(item_res)

            if not item_res.top5_match:
                failed_cases.append(
                    FailedCaseRecord(
                        item_id=item_res.item_id,
                        question=item_res.question,
                        expected_document=item_res.expected_document,
                        category=item_res.category,
                        difficulty=item_res.difficulty,
                        perspective=item_res.perspective,
                        retrieved_documents=item_res.top5_retrieved,
                        similarity_scores=item_res.retrieved_scores,
                        retrieval_rank=item_res.retrieval_rank,
                        failure_reason=item_res.failure_reason or "Target document not in top 5",
                    )
                )

        category_breakdown: Dict[str, RetrievalCategoryMetrics] = {}
        for cat_name, cat_items in category_map.items():
            category_breakdown[cat_name] = compute_category_metrics(cat_name, cat_items)

        # Compute overall aggregate metrics
        top1_total = sum(1 for x in evaluated_results if x.top1_match)
        top3_total = sum(1 for x in evaluated_results if x.top3_match)
        top5_total = sum(1 for x in evaluated_results if x.top5_match)
        successes = top5_total
        failures = total_queries - successes

        all_latencies = [x.latency_ms for x in evaluated_results]
        mrr_total = sum(x.reciprocal_rank for x in evaluated_results)

        import statistics
        mean_lat = statistics.mean(all_latencies) if all_latencies else 0.0
        median_lat = statistics.median(all_latencies) if all_latencies else 0.0
        p95_lat = calculate_percentile(all_latencies, 95.0)

        overall_report = RetrievalAggregateReport(
            timestamp=timestamp,
            total_queries=total_queries,
            overall_success_count=successes,
            overall_failure_count=failures,
            overall_success_rate=successes / float(total_queries),
            overall_failure_rate=failures / float(total_queries),
            overall_recall_at_1=top1_total / float(total_queries),
            overall_recall_at_3=top3_total / float(total_queries),
            overall_recall_at_5=top5_total / float(total_queries),
            overall_mrr=mrr_total / float(total_queries),
            overall_mean_latency_ms=mean_lat,
            overall_median_latency_ms=median_lat,
            overall_p95_latency_ms=p95_lat,
            category_breakdown=category_breakdown,
            item_results=evaluated_results,
            failed_cases=failed_cases,
        )

        logger.info(
            f"Retrieval Benchmark completed: {total_queries} queries evaluated across {len(category_breakdown)} categories. "
            f"Recall@1: {overall_report.overall_recall_at_1*100:.1f}%, Recall@5: {overall_report.overall_recall_at_5*100:.1f}%, MRR: {overall_report.overall_mrr:.4f}"
        )
        return overall_report
