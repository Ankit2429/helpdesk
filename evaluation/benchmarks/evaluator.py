"""RAG Evaluator Module.

This module houses the core RAGEvaluator class responsible for loading benchmark
datasets, executing retrieval and response generation tests against a pluggable RAG
interface, and aggregating metric scores across categories.
"""

import json
import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from evaluation.benchmarks.metrics import (
    AggregateBenchmarkReport,
    CategoryMetrics,
    DatasetRecord,
    EvaluationItemResult,
    exact_match_score,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    token_f1_score,
)

logger = logging.getLogger(__name__)


# Type definition for pluggable RAG invocation function:
# Query string -> (List of retrieved document strings, Generated answer string)
RAGCallable = Callable[[str], Tuple[List[str], str]]


class RAGEvaluator:
    """Core evaluation engine for RAG benchmarking."""

    def __init__(
        self,
        dataset_dir: Union[str, Path] = "evaluation/datasets",
        top_k: int = 5,
        rag_pipeline: Optional[RAGCallable] = None,
    ):
        """Initializes the RAG evaluator.

        Args:
            dataset_dir: Path to the datasets directory containing JSON benchmark files.
            top_k: Cut-off rank depth for Precision@K, Recall@K, NDCG@K.
            rag_pipeline: Optional callable function taking a query string and returning
                          (retrieved_docs, generated_answer). If None, mock mode is used.
        """
        self.dataset_dir = Path(dataset_dir)
        self.top_k = top_k
        self.rag_pipeline = rag_pipeline or self._mock_rag_pipeline

    def _mock_rag_pipeline(self, query: str) -> Tuple[List[str], str]:
        """Fallback mock RAG pipeline for dry-run benchmarking without backend dependency."""
        logger.debug(f"[Mock Pipeline] Evaluated query: '{query}'")
        mock_docs = [f"Mock doc context for query: {query}"]
        mock_answer = f"Mock generated answer for query: {query}"
        return mock_docs, mock_answer

    def load_dataset_file(self, file_path: Path) -> List[DatasetRecord]:
        """Loads dataset records from a single JSON file.

        Args:
            file_path: Path to dataset JSON file.

        Returns:
            List of parsed DatasetRecord instances.
        """
        if not file_path.exists():
            logger.warning(f"Dataset file not found: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, list):
                logger.error(f"Invalid dataset format in {file_path}. Expected JSON list.")
                return []

            records = []
            for item in raw_data:
                record = DatasetRecord(
                    id=item.get("id", len(records) + 1),
                    question=item.get("question", ""),
                    expected_document=item.get("expected_document", ""),
                    expected_answer=item.get("expected_answer", ""),
                    category=item.get("category", file_path.stem.capitalize()),
                    expected_chunks=item.get("expected_chunks", []),
                    metadata=item.get("metadata", {}),
                    difficulty=item.get("difficulty", "medium"),
                    keywords=item.get("keywords", []),
                    synonyms=item.get("synonyms", []),
                )
                records.append(record)

            logger.info(f"Loaded {len(records)} benchmark records from {file_path.name}")
            return records

        except Exception as e:
            logger.error(f"Failed to load dataset file {file_path}: {e}")
            return []

    def load_all_datasets(self, category_filter: Optional[str] = None) -> List[DatasetRecord]:
        """Loads all benchmark datasets from the dataset directory.

        Args:
            category_filter: Optional category name to filter datasets (case-insensitive).

        Returns:
            Combined list of DatasetRecord items across matching dataset files.
        """
        all_records: List[DatasetRecord] = []

        if not self.dataset_dir.exists():
            logger.error(f"Dataset directory does not exist: {self.dataset_dir}")
            return all_records

        json_files = list(self.dataset_dir.glob("*.json"))
        for json_file in sorted(json_files):
            records = self.load_dataset_file(json_file)
            if category_filter:
                filtered = [
                    r for r in records
                    if r.category.lower() == category_filter.lower() or json_file.stem.lower() == category_filter.lower()
                ]
                all_records.extend(filtered)
            else:
                all_records.extend(records)

        logger.info(f"Total benchmark dataset records loaded: {len(all_records)}")
        return all_records

    def evaluate_item(self, record: DatasetRecord) -> EvaluationItemResult:
        """Evaluates a single benchmark record against the RAG pipeline.

        Args:
            record: DatasetRecord instance containing target question & expected targets.

        Returns:
            EvaluationItemResult containing metric scores and timing information.
        """
        start_time = time.perf_counter()

        try:
            retrieved_docs, generated_answer = self.rag_pipeline(record.question)
        except Exception as e:
            logger.error(f"Error invoking RAG pipeline for item ID {record.id}: {e}")
            retrieved_docs, generated_answer = [], ""

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        p_at_k = precision_at_k(retrieved_docs, record.expected_document, k=self.top_k)
        r_at_k = recall_at_k(retrieved_docs, record.expected_document, k=self.top_k)
        mrr_val = mean_reciprocal_rank(retrieved_docs, record.expected_document)
        hr_at_k = hit_rate_at_k(retrieved_docs, record.expected_document, k=self.top_k)
        ndcg_val = ndcg_at_k(retrieved_docs, record.expected_document, k=self.top_k)

        em_val = exact_match_score(generated_answer, record.expected_answer)
        f1_val = token_f1_score(generated_answer, record.expected_answer)

        # Basic pass condition: hit rate >= 1.0 or token F1 >= 0.5
        passed = (hr_at_k >= 1.0 or f1_val >= 0.5)

        return EvaluationItemResult(
            item_id=record.id,
            question=record.question,
            category=record.category,
            expected_document=record.expected_document,
            retrieved_documents=retrieved_docs,
            expected_answer=record.expected_answer,
            generated_answer=generated_answer,
            latency_ms=elapsed_ms,
            precision_at_k=p_at_k,
            recall_at_k=r_at_k,
            mrr=mrr_val,
            hit_rate=hr_at_k,
            ndcg_at_k=ndcg_val,
            exact_match=em_val,
            token_f1=f1_val,
            semantic_similarity=0.0,  # Placeholder for future embeddings score
            passed=passed,
            metadata=record.metadata,
        )

    def run_benchmark(
        self,
        category_filter: Optional[str] = None,
        dataset_records: Optional[List[DatasetRecord]] = None,
    ) -> AggregateBenchmarkReport:
        """Executes the full evaluation suite and returns aggregate metrics.

        Args:
            category_filter: Optional category name filter.
            dataset_records: Optional pre-loaded list of records. If None, loaded from files.

        Returns:
            AggregateBenchmarkReport summarizing overall performance and category breakdowns.
        """
        records = dataset_records or self.load_all_datasets(category_filter=category_filter)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not records:
            logger.warning("No records found to evaluate.")
            return AggregateBenchmarkReport(
                timestamp=timestamp,
                total_queries=0,
                top_k=self.top_k,
                overall_precision_at_k=0.0,
                overall_recall_at_k=0.0,
                overall_mrr=0.0,
                overall_hit_rate=0.0,
                overall_ndcg_at_k=0.0,
                overall_exact_match=0.0,
                overall_token_f1=0.0,
                overall_mean_latency_ms=0.0,
                overall_pass_rate=0.0,
            )

        item_results: List[EvaluationItemResult] = []
        category_map: Dict[str, List[EvaluationItemResult]] = {}

        for record in records:
            res = self.evaluate_item(record)
            item_results.append(res)
            category_map.setdefault(res.category, []).append(res)

        # Compute category-level metrics
        category_breakdown: Dict[str, CategoryMetrics] = {}
        for cat_name, cat_items in category_map.items():
            count = len(cat_items)
            category_breakdown[cat_name] = CategoryMetrics(
                category=cat_name,
                total_queries=count,
                mean_precision_at_k=sum(x.precision_at_k for x in cat_items) / count,
                mean_recall_at_k=sum(x.recall_at_k for x in cat_items) / count,
                mean_mrr=sum(x.mrr for x in cat_items) / count,
                mean_hit_rate=sum(x.hit_rate for x in cat_items) / count,
                mean_ndcg_at_k=sum(x.ndcg_at_k for x in cat_items) / count,
                mean_exact_match=sum(x.exact_match for x in cat_items) / count,
                mean_token_f1=sum(x.token_f1 for x in cat_items) / count,
                mean_latency_ms=sum(x.latency_ms for x in cat_items) / count,
                pass_rate=sum(1.0 for x in cat_items if x.passed) / count,
            )

        total_count = len(item_results)
        overall_report = AggregateBenchmarkReport(
            timestamp=timestamp,
            total_queries=total_count,
            top_k=self.top_k,
            overall_precision_at_k=sum(x.precision_at_k for x in item_results) / total_count,
            overall_recall_at_k=sum(x.recall_at_k for x in item_results) / total_count,
            overall_mrr=sum(x.mrr for x in item_results) / total_count,
            overall_hit_rate=sum(x.hit_rate for x in item_results) / total_count,
            overall_ndcg_at_k=sum(x.ndcg_at_k for x in item_results) / total_count,
            overall_exact_match=sum(x.exact_match for x in item_results) / total_count,
            overall_token_f1=sum(x.token_f1 for x in item_results) / total_count,
            overall_mean_latency_ms=sum(x.latency_ms for x in item_results) / total_count,
            overall_pass_rate=sum(1.0 for x in item_results if x.passed) / total_count,
            category_breakdown=category_breakdown,
            individual_results=item_results,
        )

        logger.info(f"Completed benchmark run for {total_count} items across {len(category_breakdown)} categories.")
        return overall_report
