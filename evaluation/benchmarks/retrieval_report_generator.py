"""Retrieval Report Generator Module.

Exports evaluation results into Markdown reports, structured JSON dumps,
failed cases analysis files, and CSV category metric summaries under evaluation/reports/.
"""
# ruff: noqa: E501
import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path

from evaluation.benchmarks.retrieval_metrics import (
    RetrievalAggregateReport,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants – centralised for easy adjustment and reuse throughout
# the report generation logic.
# ---------------------------------------------------------------------------
THRESHOLDS = {
    "recall_at_1": 0.80,
    "recall_at_3": 0.85,
    "recall_at_5": 0.90,
    "mrr": 0.85,
    "success_rate": 0.90,
    "failure_rate": 0.10,
    "p95_latency_ms": 100.0,
    "mean_latency_ms": 50.0,
    "median_latency_ms": 30.0,
    # Future thresholds for optional metrics can be added here
}


class ReportGenerationError(RuntimeError):
    """Custom exception for unrecoverable errors during report generation."""


class RetrievalReportGenerator:
    """Formatter and exporter for retrieval benchmarking reports.

    The class focuses on **rendering** Markdown, JSON, CSV and failure‑case
    files from a populated :class:`RetrievalAggregateReport`. All file‑system
    interactions are guarded with error handling and optional overwrite
    protection.
    """

    def __init__(self, output_dir: str | Path = "evaluation/reports"):
        """Initialises report generator with output directory.

        Parameters
        ----------
        output_dir: Union[str, Path]
            Destination folder for all generated artefacts. It is created if it
            does not exist and resolved to an absolute path.
        """
        self.output_dir = Path(output_dir).resolve()
        # Ensure the output directory exists.
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------
    @staticmethod
    def _format_percentage(value: float | None) -> str:
        """Return a human‑readable percentage string or ``"N/A"``.

        ``value`` is expected to be in the ``0.0‑1.0`` range.
        """
        if isinstance(value, (int, float)):
            return f"{value * 100.0:.2f}%"
        return "N/A"

    @staticmethod
    def _format_float(value: float | None, fmt: str = ".4f") -> str:
        if isinstance(value, (int, float)):
            return f"{value:{fmt}}"
        return "N/A"

    def _write_file(self, path: Path, content: str, overwrite: bool = False) -> None:
        """Safely write *content* to *path*.

        Raises
        ------
        FileExistsError
            If ``overwrite`` is ``False`` and the file already exists.
        ReportGenerationError
            For any underlying OS‑level problem.
        """
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"File {path} already exists. Use overwrite=True to replace."
            )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            logger.error(f"Failed to write {path}: {exc}")
            raise ReportGenerationError(str(exc)) from exc

    def _validate_report(self, report: RetrievalAggregateReport) -> None:
        """Validate that required numeric fields are within sensible bounds.

        This method raises ``ValueError`` if a metric is missing or out of range.
        """
        numeric_fields = [
            "overall_recall_at_1",
            "overall_recall_at_3",
            "overall_recall_at_5",
            "overall_mrr",
            "overall_success_rate",
            "overall_failure_rate",
            "overall_mean_latency_ms",
            "overall_median_latency_ms",
            "overall_p95_latency_ms",
        ]
        for field in numeric_fields:
            value = getattr(report, field, None)
            if value is None:
                raise ValueError(f"Report is missing required field '{field}'.")
            if not isinstance(value, (int, float)):
                raise ValueError(f"Field '{field}' must be numeric, got {type(value)}.")
            if "latency" in field.lower():
                if value < 0:
                    raise ValueError(f"Latency metric '{field}' cannot be negative.")
            else:
                if not (0.0 <= value <= 1.0):
                    raise ValueError(
                        f"Metric '{field}' out of expected 0-1 range: {value}."
                    )

    # ---------------------------------------------------------------------
    # Rendering
    # ---------------------------------------------------------------------
    def generate_markdown(self, report: RetrievalAggregateReport) -> str:
        """Render the comprehensive retrieval evaluation report in GitHub‑flavoured Markdown.

        The method assumes the *report* object has already been validated.
        """
        self._validate_report(report)
        lines: list[str] = []
        lines.append("# RAG Vector & Hybrid Retrieval Benchmark Report")
        lines.append("")
        lines.append(f"- **Timestamp**: `{report.timestamp}`")
        lines.append(f"- **Total Benchmark Queries**: `{report.total_queries}`")
        lines.append(
            f"- **Overall Success Rate (Top‑5 Match)**: `{self._format_percentage(report.overall_success_rate)}`"
        )
        lines.append(
            f"- **Overall Mean Reciprocal Rank (MRR)**: `{self._format_float(report.overall_mrr, '.4f')}`"
        )
        lines.append(
            f"- **P95 Retrieval Latency**: `{report.overall_p95_latency_ms:.2f} ms`"
        )
        lines.append("")

        # -----------------------------------------------------------------
        # 1. Executive Summary Table
        # -----------------------------------------------------------------
        lines.append("## Executive Summary Metrics")
        lines.append("")
        lines.append("| Metric | Score | Production Threshold | Status |")
        lines.append("| :--- | :---: | :---: | :---: |")

        r1_status = (
            "PASS"
            if report.overall_recall_at_1 >= THRESHOLDS["recall_at_1"]
            else "NEEDS OPTIMIZATION"
        )
        r3_status = (
            "PASS"
            if report.overall_recall_at_3 >= THRESHOLDS["recall_at_3"]
            else "NEEDS OPTIMIZATION"
        )
        r5_status = (
            "PASS"
            if report.overall_recall_at_5 >= THRESHOLDS["recall_at_5"]
            else "NEEDS OPTIMIZATION"
        )
        mrr_status = (
            "PASS"
            if report.overall_mrr >= THRESHOLDS["mrr"]
            else "NEEDS OPTIMIZATION"
        )
        lat_status = (
            "PASS"
            if report.overall_p95_latency_ms <= THRESHOLDS["p95_latency_ms"]
            else "NEEDS OPTIMIZATION"
        )
        success_status = (
            "PASS"
            if report.overall_success_rate >= THRESHOLDS["success_rate"]
            else "NEEDS OPTIMIZATION"
        )

        lines.append(
            f"| **Recall@1** | `{self._format_percentage(report.overall_recall_at_1)}` | `>={THRESHOLDS['recall_at_1']*100:.0f}%` | **{r1_status}** |"
        )
        lines.append(
            f"| **Recall@3** | `{self._format_percentage(report.overall_recall_at_3)}` | `>={THRESHOLDS['recall_at_3']*100:.0f}%` | **{r3_status}** |"
        )
        lines.append(
            f"| **Recall@5** | `{self._format_percentage(report.overall_recall_at_5)}` | `>={THRESHOLDS['recall_at_5']*100:.0f}%` | **{r5_status}** |"
        )
        lines.append(
            f"| **Mean Reciprocal Rank (MRR)** | `{self._format_float(report.overall_mrr, '.4f')}` | `>={THRESHOLDS['mrr']:.4f}` | **{mrr_status}** |"
        )
        lines.append(
            f"| **Success Rate** | `{self._format_percentage(report.overall_success_rate)}` | `>={THRESHOLDS['success_rate']*100:.0f}%` | **{success_status}** |"
        )
        lines.append(
            f"| **Failure Rate** | `{self._format_percentage(report.overall_failure_rate)}` | `<= {THRESHOLDS['failure_rate']*100:.0f}%` | - |"
        )
        lines.append(
            f"| **Mean Latency** | `{report.overall_mean_latency_ms:.2f} ms` | `<= {THRESHOLDS['mean_latency_ms']:.0f} ms` | - |"
        )
        lines.append(
            f"| **Median Latency** | `{report.overall_median_latency_ms:.2f} ms` | `<= {THRESHOLDS['median_latency_ms']:.0f} ms` | - |"
        )
        lines.append(
            f"| **P95 Latency** | `{report.overall_p95_latency_ms:.2f} ms` | `<= {THRESHOLDS['p95_latency_ms']:.0f} ms` | **{lat_status}** |"
        )
        lines.append("")

        # -----------------------------------------------------------------
        # 2. Visualizations Section
        # -----------------------------------------------------------------
        lines.append("## Retrieval Visualizations")
        lines.append("")
        lines.append(
            "![Recall by Category](file:///d:/AUNTII/evaluation/reports/plots/recall_by_category.png)"
        )
        lines.append(
            "![Overall Accuracy](file:///d:/AUNTII/evaluation/reports/plots/overall_accuracy.png)"
        )
        lines.append(
            "![Latency Distribution](file:///d:/AUNTII/evaluation/reports/plots/latency_distribution.png)"
        )
        lines.append(
            "![Failure Count by Category](file:///d:/AUNTII/evaluation/reports/plots/failure_count_by_category.png)"
        )
        lines.append("")

        # -----------------------------------------------------------------
        # 3. Category Breakdown Table
        # -----------------------------------------------------------------
        lines.append("## Domain Category Performance Breakdown")
        lines.append("")
        if report.category_breakdown:
            lines.append(
                "| Category | Total Queries | Success Rate | Recall@1 | Recall@3 | Recall@5 | MRR | Mean Latency | P95 Latency |"
            )
            lines.append(
                "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
            )
            for cat_name, cat in report.category_breakdown.items():
                lines.append(
                    f"| **{cat_name}** | {cat.total_queries} | {cat.success_rate*100.0:.1f}% | "
                    f"{cat.recall_at_1*100.0:.1f}% | {cat.recall_at_3*100.0:.1f}% | {cat.recall_at_5*100.0:.1f}% | "
                    f"{cat.mrr:.4f} | {cat.mean_latency_ms:.2f} ms | {cat.p95_latency_ms:.2f} ms |"
                )
        else:
            lines.append("*No categories evaluated.*")
        lines.append("")

        # -----------------------------------------------------------------
        # 4. Failure Analysis Summary
        # -----------------------------------------------------------------
        lines.append("## Failure Analysis Summary")
        lines.append("")
        lines.append(
            f"- **Total Failed Retrievals**: `{len(report.failed_cases)}` items"
        )
        lines.append("")
        if report.failed_cases:
            lines.append(
                "| ID | Category | Question | Expected Document | Diagnosed Failure Reason |"
            )
            lines.append("| :---: | :--- | :--- | :--- | :--- |")
            for case in report.failed_cases[
                :25
            ]:  # Display top 25 failed cases in markdown
                q_sub = case.question.replace("|", "-")
                if len(q_sub) > 40:
                    q_sub = q_sub[:37] + "..."
                lines.append(
                    f"| {case.item_id} | {case.category} | {q_sub} | `{case.expected_document}` | {case.failure_reason} |"
                )

            if len(report.failed_cases) > 25:
                lines.append(
                    f"\n*...and {len(report.failed_cases) - 25} more. Full failure traces saved to `evaluation/reports/failed_cases.json`.*"
                )
        else:
            lines.append(
                "🎉 *Zero retrieval failures detected! All target documents retrieved within Top 5.*"
            )
        lines.append("")

        # -----------------------------------------------------------------
        # 5. Interpretation & Decision Guidelines
        # -----------------------------------------------------------------
        lines.append("## How to Interpret Metrics & Decide Next Steps")
        lines.append("")
        lines.append("### Metric Definitions & Target Benchmarks")
        lines.append("1. **Recall@1 (Target: >= 80%)**:")
        lines.append(
            "   - *Meaning*: The exact target document is returned as the #1 top‑ranked search result."
        )
        lines.append(
            "   - *Decision Rule*: If Recall@1 < 80%, the retriever needs stronger term re‑weighting (e.g. BM25 tuning or cross‑encoder reranking)."
        )
        lines.append("")
        lines.append("2. **Recall@3 & Recall@5 (Target: >= 90%)**:")
        lines.append(
            "   - *Meaning*: The target document is included within the top 3 or top 5 search context blocks."
        )
        lines.append(
            "   - *Decision Rule*: If Recall@5 < 90%, embedding chunk size or vector index coverage is inadequate and requires re‑indexing."
        )
        lines.append("")
        lines.append("3. **Mean Reciprocal Rank (MRR) (Target: >= 0.8500)**:")
        lines.append(
            "   - *Meaning*: Evaluates average position rank quality ($1/\\text{rank}$). A score of 1.0 means perfect #1 ranking."
        )
        lines.append(
            "   - *Decision Rule*: If MRR < 0.85, search result ordering is sub‑optimal."
        )
        lines.append("")
        lines.append("4. **P95 Latency (Target: <= 100 ms)**:")
        lines.append(
            "   - *Meaning*: 95% of helpdesk queries retrieve results in under 100 ms."
        )
        lines.append(
            "   - *Decision Rule*: If P95 Latency > 100 ms, optimize vector search index (FAISS HNSW or IVF index quantization)."
        )
        lines.append("")

        return "\n".join(lines)

    # ---------------------------------------------------------------------
    # Persistence helpers – each method now uses the safe _write_file helper.
    # ---------------------------------------------------------------------
    def save_markdown_report(
        self,
        report: RetrievalAggregateReport,
        filename: str = "retrieval_report.md",
        overwrite: bool = False,
    ) -> Path:
        """Save formatted Markdown report to disk.

        Parameters
        ----------
        report: RetrievalAggregateReport
            The data to render.
        filename: str
            Target markdown file name.
        overwrite: bool, default False
            Whether to replace an existing file.
        """
        out_file = self.output_dir / filename
        content = self.generate_markdown(report)
        self._write_file(out_file, content, overwrite=overwrite)
        logger.info(f"Saved Markdown report to {out_file}")
        return out_file

    def save_json_report(
        self,
        report: RetrievalAggregateReport,
        filename: str = "retrieval_report.json",
        overwrite: bool = False,
    ) -> Path:
        """Save full structured JSON report to disk.

        Parameters are identical to :meth:`save_markdown_report`.
        """
        out_file = self.output_dir / filename
        data = asdict(report)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        self._write_file(out_file, content, overwrite=overwrite)
        logger.info(f"Saved JSON report to {out_file}")
        return out_file

    def save_failed_cases_json(
        self,
        report: RetrievalAggregateReport,
        filename: str = "failed_cases.json",
        overwrite: bool = False,
    ) -> Path:
        """Save detailed failure analysis cases to a dedicated JSON file.

        The JSON structure is a list of case dictionaries.
        """
        out_file = self.output_dir / filename
        cases_data = [asdict(fc) for fc in report.failed_cases]
        content = json.dumps(cases_data, indent=2, ensure_ascii=False)
        self._write_file(out_file, content, overwrite=overwrite)
        logger.info(
            f"Saved failed cases analysis ({len(cases_data)} items) to {out_file}"
        )
        return out_file

    def save_summary_csv(
        self,
        report: RetrievalAggregateReport,
        filename: str = "summary.csv",
        overwrite: bool = False,
    ) -> Path:
        """Export category metric summary table into a CSV file.

        Parameters are identical to :meth:`save_markdown_report`.
        """
        out_file = self.output_dir / filename
        if out_file.exists() and not overwrite:
            raise FileExistsError(
                f"CSV file {out_file} already exists. Use overwrite=True to replace."
            )
        fieldnames = [
            "Category",
            "TotalQueries",
            "SuccessRate",
            "FailureRate",
            "Recall@1",
            "Recall@3",
            "Recall@5",
            "MRR",
            "MeanLatencyMS",
            "MedianLatencyMS",
            "P95LatencyMS",
        ]
        try:
            with open(out_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for cat_name, cat in report.category_breakdown.items():
                    writer.writerow(
                        {
                            "Category": cat_name,
                            "TotalQueries": cat.total_queries,
                            "SuccessRate": f"{cat.success_rate * 100.0:.2f}%",
                            "FailureRate": f"{cat.failure_rate * 100.0:.2f}%",
                            "Recall@1": f"{cat.recall_at_1 * 100.0:.2f}%",
                            "Recall@3": f"{cat.recall_at_3 * 100.0:.2f}%",
                            "Recall@5": f"{cat.recall_at_5 * 100.0:.2f}%",
                            "MRR": f"{cat.mrr:.4f}",
                            "MeanLatencyMS": f"{cat.mean_latency_ms:.2f}",
                            "MedianLatencyMS": f"{cat.median_latency_ms:.2f}",
                            "P95LatencyMS": f"{cat.p95_latency_ms:.2f}",
                        }
                    )
        except OSError as exc:
            logger.error(f"Failed to write CSV {out_file}: {exc}")
            raise ReportGenerationError(str(exc)) from exc
        logger.info(f"Exported summary CSV to {out_file}")
        return out_file

    def generate_all_reports(
        self, report: RetrievalAggregateReport, overwrite: bool = False
    ) -> dict[str, Path]:
        """Generates all report output files.

        Returns a mapping from report type to the path of the generated file.
        """
        return {
            "markdown": self.save_markdown_report(report, overwrite=overwrite),
            "json": self.save_json_report(report, overwrite=overwrite),
            "failed_cases": self.save_failed_cases_json(report, overwrite=overwrite),
            "csv": self.save_summary_csv(report, overwrite=overwrite),
        }
