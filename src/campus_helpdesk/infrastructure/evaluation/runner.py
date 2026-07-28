"""Automated EvaluationRunner for measuring RAG retrieval, reranking, and generation metrics."""

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.infrastructure.evaluation.metrics import (
    calculate_keyword_coverage,
    calculate_mrr,
    calculate_recall_at_k,
)

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Runs automated benchmark evaluations across dataset questions and outputs summary reports."""

    def __init__(
        self,
        pipeline: RAGPipeline,
        dataset_path: Path | str = "evaluation/questions.yaml",
        output_dir: Path | str = "evaluation/results",
    ) -> None:
        self.pipeline = pipeline
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load benchmark dataset from YAML or JSON format."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Evaluation dataset not found at {self.dataset_path}")

        content = self.dataset_path.read_text(encoding="utf-8")
        try:
            import yaml
            data = yaml.safe_load(content)
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            elif isinstance(data, list):
                return data
        except Exception as err:
            logger.warning("YAML parsing failed, attempting fallback JSON parse: %s", err)
            data = json.loads(content)
            return data.get("questions", data) if isinstance(data, dict) else data

        return []

    def run_evaluation(self, run_llm_generation: bool = False) -> dict[str, Any]:
        """Execute full benchmark evaluation suite across all questions in dataset."""
        questions = self.load_dataset()
        if not questions:
            raise ValueError("No valid questions found in evaluation dataset.")

        start_time = time.perf_counter()
        results: list[dict[str, Any]] = []
        category_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "recall5_sum": 0.0, "recall10_sum": 0.0, "mrr_sum": 0.0, "kw_sum": 0.0}
        )

        total_recall5 = 0.0
        total_recall10 = 0.0
        total_mrr = 0.0
        total_kw_coverage = 0.0
        total_latency = 0.0

        for q in questions:
            qid = q.get("id", "UNKNOWN")
            cat = q.get("category", "General")
            query = q.get("question", "")
            exp_keywords = q.get("expected_answer_keywords", [])
            exp_sources = q.get("expected_sources", [])

            t0 = time.perf_counter()
            retrieved_matches = self.pipeline.search(query, limit=10)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            retrieved_sources = [m.document.metadata.get("source", "") for m in retrieved_matches]
            combined_context = "\n".join([m.document.content for m in retrieved_matches])

            from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
            conf_engine = ConfidenceEngine()
            assessment = conf_engine.evaluate(retrieved_matches)

            recall5 = calculate_recall_at_k(retrieved_sources, exp_sources, k=5)
            recall10 = calculate_recall_at_k(retrieved_sources, exp_sources, k=10)
            mrr = calculate_mrr(retrieved_sources, exp_sources)
            kw_coverage, matched_kws, missing_kws = calculate_keyword_coverage(combined_context, exp_keywords)

            # Record question metrics
            q_result = {
                "id": qid,
                "category": cat,
                "question": query,
                "latency_ms": latency_ms,
                "recall_at_5": round(recall5, 4),
                "recall_at_10": round(recall10, 4),
                "mrr": round(mrr, 4),
                "keyword_coverage": round(kw_coverage, 4),
                "confidence_score": assessment.confidence_score,
                "confidence_level": assessment.confidence_level,
                "matched_keywords": matched_kws,
                "missing_keywords": missing_kws,
                "retrieved_sources": retrieved_sources[:5],
            }
            results.append(q_result)

            # Aggregate statistics
            total_recall5 += recall5
            total_recall10 += recall10
            total_mrr += mrr
            total_kw_coverage += kw_coverage
            total_latency += latency_ms

            cat_s = category_stats[cat]
            cat_s["count"] += 1
            cat_s["recall5_sum"] += recall5
            cat_s["recall10_sum"] += recall10
            cat_s["mrr_sum"] += mrr
            cat_s["kw_sum"] += kw_coverage

        total_q = len(questions)
        overall_recall5 = round(total_recall5 / total_q, 4)
        overall_recall10 = round(total_recall10 / total_q, 4)
        overall_mrr = round(total_mrr / total_q, 4)
        overall_kw_cov = round(total_kw_coverage / total_q, 4)
        avg_confidence = round(sum(q["confidence_score"] for q in results) / total_q, 4)
        conf_dist = {
            "HIGH": sum(1 for q in results if q["confidence_level"] == "HIGH"),
            "MEDIUM": sum(1 for q in results if q["confidence_level"] == "MEDIUM"),
            "LOW": sum(1 for q in results if q["confidence_level"] == "LOW"),
        }
        overall_score = round((overall_recall5 + overall_mrr + overall_kw_cov) / 3.0 * 100, 2)
        avg_latency = round(total_latency / total_q, 2)
        total_duration = round(time.perf_counter() - start_time, 2)

        per_category_report = {}
        for cname, cstat in category_stats.items():
            cnt = cstat["count"]
            per_category_report[cname] = {
                "question_count": cnt,
                "recall_at_5": round(cstat["recall5_sum"] / cnt, 4),
                "recall_at_10": round(cstat["recall10_sum"] / cnt, 4),
                "mrr": round(cstat["mrr_sum"] / cnt, 4),
                "keyword_coverage": round(cstat["kw_sum"] / cnt, 4),
                "accuracy_score": round((cstat["recall5_sum"] + cstat["mrr_sum"] + cstat["kw_sum"]) / (3.0 * cnt) * 100, 2),
            }

        summary_report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_questions": total_q,
            "overall_score": overall_score,
            "overall_recall_at_5": overall_recall5,
            "overall_recall_at_10": overall_recall10,
            "overall_mrr": overall_mrr,
            "overall_keyword_coverage": overall_kw_cov,
            "average_confidence_score": avg_confidence,
            "confidence_distribution": conf_dist,
            "average_retrieval_latency_ms": avg_latency,
            "evaluation_duration_seconds": total_duration,
            "per_category_accuracy": per_category_report,
            "detailed_results": results,
        }

        self._save_reports(summary_report)
        return summary_report

    def _save_reports(self, report: dict[str, Any]) -> None:
        """Persist summary.json and summary.md reports to output_dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save JSON Report
        json_path = self.output_dir / "summary.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Saved JSON evaluation summary to %s", json_path)

        # 2. Save Markdown Report
        md_path = self.output_dir / "summary.md"
        md_lines = [
            "# Campus Helpdesk Robot RAG Evaluation Summary Report",
            "",
            f"**Timestamp**: {report['timestamp']}  ",
            f"**Total Benchmark Questions**: {report['total_questions']}  ",
            f"**Overall RAG Quality Score**: **{report['overall_score']}%**  ",
            f"**Average Retrieval Latency**: {report['average_retrieval_latency_ms']} ms  ",
            "",
            "## Aggregate Metric Overview",
            "",
            "| Metric | Score |",
            "|---|---|",
            f"| **Overall RAG Quality Score** | **{report['overall_score']}%** |",
            f"| **Recall@5** | {report['overall_recall_at_5']:.2%} |",
            f"| **Recall@10** | {report['overall_recall_at_10']:.2%} |",
            f"| **Mean Reciprocal Rank (MRR)** | {report['overall_mrr']:.4f} |",
            f"| **Keyword Coverage** | {report['overall_keyword_coverage']:.2%} |",
            "",
            "## Per-Category Accuracy Breakdown",
            "",
            "| Category | Questions | Recall@5 | Recall@10 | MRR | Keyword Coverage | Category Accuracy |",
            "|---|---|---|---|---|---|---|",
        ]

        for cat, cstat in report["per_category_accuracy"].items():
            md_lines.append(
                f"| **{cat}** | {cstat['question_count']} | {cstat['recall_at_5']:.2%} | "
                f"{cstat['recall_at_10']:.2%} | {cstat['mrr']:.4f} | {cstat['keyword_coverage']:.2%} | "
                f"**{cstat['accuracy_score']}%** |"
            )

        md_lines.extend(
            [
                "",
                "## Question-Level Diagnostics",
                "",
                "| ID | Category | Question | Recall@5 | MRR | KW Coverage | Latency |",
                "|---|---|---|---|---|---|---|",
            ]
        )

        for q in report["detailed_results"]:
            md_lines.append(
                f"| `{q['id']}` | {q['category']} | {q['question'][:45]}... | {q['recall_at_5']} | "
                f"{q['mrr']} | {q['keyword_coverage']:.2%} | {q['latency_ms']}ms |"
            )

        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        logger.info("Saved Markdown evaluation summary to %s", md_path)
