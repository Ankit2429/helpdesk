"""Report Generator Module for RAG Evaluation Benchmark.

This module provides the ReportGenerator class, which transforms evaluation
results into Markdown reports, structured JSON exports, and clean terminal output tables.
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Union

from evaluation.benchmarks.metrics import AggregateBenchmarkReport

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Formatter and exporter for evaluation benchmark reports."""

    def __init__(self, output_dir: Union[str, Path] = "evaluation/reports"):
        """Initializes the report generator.

        Args:
            output_dir: Destination directory where report files will be written.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown(self, report: AggregateBenchmarkReport) -> str:
        """Renders the evaluation report in GitHub-flavored Markdown.

        Args:
            report: AggregateBenchmarkReport object.

        Returns:
            Formatted Markdown string.
        """
        md_lines = []
        md_lines.append("# RAG Retrieval & Benchmark Evaluation Report")
        md_lines.append("")
        md_lines.append(f"- **Timestamp**: `{report.timestamp}`")
        md_lines.append(f"- **Total Queries Evaluated**: `{report.total_queries}`")
        md_lines.append(f"- **Retrieval Cut-off (K)**: `{report.top_k}`")
        md_lines.append(f"- **Overall Pass Rate**: `{report.overall_pass_rate * 100.0:.2f}%`")
        md_lines.append("")

        # Executive Summary Table
        md_lines.append("## Executive Summary Metrics")
        md_lines.append("")
        md_lines.append("| Metric | Score | Description |")
        md_lines.append("| :--- | :---: | :--- |")
        md_lines.append(f"| **Precision@{report.top_k}** | `{report.overall_precision_at_k:.4f}` | Relevant documents in top-K |")
        md_lines.append(f"| **Recall@{report.top_k}** | `{report.overall_recall_at_k:.4f}` | Target documents retrieved |")
        md_lines.append(f"| **MRR** | `{report.overall_mrr:.4f}` | Mean Reciprocal Rank |")
        md_lines.append(f"| **Hit Rate@{report.top_k}** | `{report.overall_hit_rate:.4f}` | Queries with >= 1 relevant doc in top-K |")
        md_lines.append(f"| **NDCG@{report.top_k}** | `{report.overall_ndcg_at_k:.4f}` | Ranking relevance discount score |")
        md_lines.append(f"| **Exact Match** | `{report.overall_exact_match:.4f}` | String exact equality ratio |")
        md_lines.append(f"| **Token F1** | `{report.overall_token_f1:.4f}` | Token overlap harmonic mean |")
        md_lines.append(f"| **Mean Latency** | `{report.overall_mean_latency_ms:.2f} ms` | Average evaluation latency |")
        md_lines.append("")

        # Category Breakdown Table
        md_lines.append("## Category Breakdown")
        md_lines.append("")
        if report.category_breakdown:
            md_lines.append("| Category | Queries | Pass Rate | P@K | R@K | MRR | Hit Rate | NDCG@K | Token F1 | Avg Latency |")
            md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
            for cat_name, cat in report.category_breakdown.items():
                md_lines.append(
                    f"| **{cat_name}** | {cat.total_queries} | {cat.pass_rate*100:.1f}% | "
                    f"{cat.mean_precision_at_k:.3f} | {cat.mean_recall_at_k:.3f} | {cat.mean_mrr:.3f} | "
                    f"{cat.mean_hit_rate:.3f} | {cat.mean_ndcg_at_k:.3f} | {cat.mean_token_f1:.3f} | "
                    f"{cat.mean_latency_ms:.1f} ms |"
                )
        else:
            md_lines.append("*No categories evaluated.*")
        md_lines.append("")

        # Detailed Query Results Table
        md_lines.append("## Detailed Item Results")
        md_lines.append("")
        if report.individual_results:
            md_lines.append("| ID | Category | Question | Hit Rate | Token F1 | Status | Latency |")
            md_lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: |")
            for item in report.individual_results:
                status_str = "PASSED" if item.passed else "FAILED"
                q_text = item.question.replace("|", "-")
                if len(q_text) > 40:
                    q_text = q_text[:37] + "..."
                md_lines.append(
                    f"| {item.item_id} | {item.category} | {q_text} | "
                    f"{item.hit_rate:.2f} | {item.token_f1:.2f} | {status_str} | {item.latency_ms:.1f} ms |"
                )
        else:
            md_lines.append("*No individual item results available.*")
        md_lines.append("")

        return "\n".join(md_lines)

    def save_markdown_report(
        self, report: AggregateBenchmarkReport, filename: str = "latest_report.md"
    ) -> Path:
        """Saves report to a Markdown file.

        Args:
            report: AggregateBenchmarkReport object.
            filename: Target markdown filename.

        Returns:
            Path object pointing to the saved file.
        """
        file_path = self.output_dir / filename
        content = self.generate_markdown(report)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved Markdown report to {file_path}")
        return file_path

    def save_json_report(
        self, report: AggregateBenchmarkReport, filename: str = "latest_report.json"
    ) -> Path:
        """Saves report data structure to a JSON file.

        Args:
            report: AggregateBenchmarkReport object.
            filename: Target JSON filename.

        Returns:
            Path object pointing to the saved JSON file.
        """
        file_path = self.output_dir / filename
        data = asdict(report)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON report to {file_path}")
        return file_path

    def print_console_summary(self, report: AggregateBenchmarkReport) -> None:
        """Prints a clean summary table to standard output."""
        print("\n" + "=" * 60)
        print("           RAG BENCHMARK EVALUATION SUMMARY")
        print("=" * 60)
        print(f" Timestamp      : {report.timestamp}")
        print(f" Total Queries  : {report.total_queries}")
        print(f" Top-K Cutoff   : {report.top_k}")
        print(f" Pass Rate      : {report.overall_pass_rate * 100.0:.2f}%")
        print("-" * 60)
        print(f" Precision@{report.top_k}  : {report.overall_precision_at_k:.4f}")
        print(f" Recall@{report.top_k}     : {report.overall_recall_at_k:.4f}")
        print(f" MRR            : {report.overall_mrr:.4f}")
        print(f" Hit Rate@{report.top_k}   : {report.overall_hit_rate:.4f}")
        print(f" NDCG@{report.top_k}       : {report.overall_ndcg_at_k:.4f}")
        print(f" Token F1       : {report.overall_token_f1:.4f}")
        print(f" Exact Match    : {report.overall_exact_match:.4f}")
        print(f" Mean Latency   : {report.overall_mean_latency_ms:.2f} ms")
        print("=" * 60 + "\n")
