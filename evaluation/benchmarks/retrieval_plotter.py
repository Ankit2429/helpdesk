"""Retrieval Visualization Charts Module.

Generates publication-quality metric visualization plots saved as PNG images
under evaluation/reports/plots/ (Recall by Category, Latency Distribution,
Failure Counts, Overall Accuracy).
Includes fallback handling if matplotlib is not installed.
"""

import logging
from pathlib import Path
from typing import Dict, List, Union

from evaluation.benchmarks.retrieval_metrics import RetrievalAggregateReport

logger = logging.getLogger(__name__)

# Optional matplotlib import with graceful fallback
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib is not installed in the Python environment. Plot generation will be skipped or generate fallback summary text files.")


class RetrievalPlotter:
    """Generates visualization charts for retrieval evaluation reports."""

    def __init__(self, plots_dir: Union[str, Path] = "evaluation/reports/plots"):
        """Initializes plotter with target destination directory."""
        self.plots_dir = Path(plots_dir)
        self.plots_dir.mkdir(parents=True, exist_ok=True)

    def plot_recall_by_category(self, report: RetrievalAggregateReport) -> Path:
        """Generates grouped bar chart of Recall@1, Recall@3, and Recall@5 by Category."""
        out_path = self.plots_dir / "recall_by_category.png"
        if not HAS_MATPLOTLIB:
            logger.info("Skipping PNG plot (matplotlib unavailable).")
            return out_path

        categories = list(report.category_breakdown.keys())
        if not categories:
            return out_path

        r1 = [cat.recall_at_1 * 100.0 for cat in report.category_breakdown.values()]
        r3 = [cat.recall_at_3 * 100.0 for cat in report.category_breakdown.values()]
        r5 = [cat.recall_at_5 * 100.0 for cat in report.category_breakdown.values()]

        x = range(len(categories))
        width = 0.25

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar([i - width for i in x], r1, width, label="Recall@1", color="#2b5c8f")
        ax.bar(x, r3, width, label="Recall@3", color="#4682b4")
        ax.bar([i + width for i in x], r5, width, label="Recall@5", color="#6baed6")

        ax.set_ylabel("Recall Rate (%)", fontsize=12, fontweight="bold")
        ax.set_title("RAG Retrieval Recall Accuracy by Domain Category", fontsize=14, fontweight="bold", pad=15)
        ax.set_xticks(list(x))
        ax.set_xticklabels(categories, rotation=25, ha="right", fontsize=10)
        ax.set_ylim(0, 105)
        ax.legend(loc="upper right", frameon=True)

        for container in ax.containers:
            ax.bar_label(container, fmt="%.0f%%", padding=3, fontsize=8)

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated chart: {out_path}")
        return out_path

    def plot_latency_distribution(self, report: RetrievalAggregateReport) -> Path:
        """Generates histogram plot of retrieval query latencies in milliseconds."""
        out_path = self.plots_dir / "latency_distribution.png"
        if not HAS_MATPLOTLIB:
            return out_path

        latencies = [item.latency_ms for item in report.item_results]
        if not latencies:
            return out_path

        fig, ax = plt.subplots(figsize=(10, 5))
        n, bins, patches = ax.hist(latencies, bins=25, color="#3182bd", edgecolor="white", alpha=0.8)

        ax.axvline(report.overall_mean_latency_ms, color="#de2d26", linestyle="--", linewidth=2, label=f"Mean: {report.overall_mean_latency_ms:.1f} ms")
        ax.axvline(report.overall_median_latency_ms, color="#31a354", linestyle="-.", linewidth=2, label=f"Median: {report.overall_median_latency_ms:.1f} ms")
        ax.axvline(report.overall_p95_latency_ms, color="#756bb1", linestyle=":", linewidth=2, label=f"P95: {report.overall_p95_latency_ms:.1f} ms")

        ax.set_xlabel("Retrieval Latency (ms)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Query Count", fontsize=12, fontweight="bold")
        ax.set_title("RAG Retrieval Query Latency Distribution", fontsize=14, fontweight="bold", pad=15)
        ax.legend(loc="upper right", frameon=True)

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated chart: {out_path}")
        return out_path

    def plot_failure_count_by_category(self, report: RetrievalAggregateReport) -> Path:
        """Generates bar chart of retrieval failure counts by domain category."""
        out_path = self.plots_dir / "failure_count_by_category.png"
        if not HAS_MATPLOTLIB:
            return out_path

        categories = list(report.category_breakdown.keys())
        if not categories:
            return out_path

        failures = [cat.failure_count for cat in report.category_breakdown.values()]

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(categories, failures, color="#e6550d", edgecolor="white", width=0.5)

        ax.set_ylabel("Failed Query Count", fontsize=12, fontweight="bold")
        ax.set_title("Retrieval Failures by Category (Target Doc Not in Top 5)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xticklabels(categories, rotation=25, ha="right", fontsize=10)

        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{int(height)}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated chart: {out_path}")
        return out_path

    def plot_overall_accuracy(self, report: RetrievalAggregateReport) -> Path:
        """Generates aggregate accuracy comparison chart (Recall@1/3/5, MRR, Success Rate)."""
        out_path = self.plots_dir / "overall_accuracy.png"
        if not HAS_MATPLOTLIB:
            return out_path

        metrics = ["Recall@1", "Recall@3", "Recall@5", "MRR", "Success Rate"]
        values = [
            report.overall_recall_at_1 * 100.0,
            report.overall_recall_at_3 * 100.0,
            report.overall_recall_at_5 * 100.0,
            report.overall_mrr * 100.0,
            report.overall_success_rate * 100.0,
        ]
        colors = ["#2b5c8f", "#4682b4", "#6baed6", "#31a354", "#756bb1"]

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(metrics, values, color=colors, width=0.45)

        ax.set_ylabel("Percentage (%) / Score", fontsize=12, fontweight="bold")
        ax.set_title("Overall RAG Retriever Accuracy Summary", fontsize=14, fontweight="bold", pad=15)
        ax.set_ylim(0, 110)

        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated chart: {out_path}")
        return out_path

    def generate_all_plots(self, report: RetrievalAggregateReport) -> Dict[str, Path]:
        """Generates all 4 visualization plots."""
        return {
            "recall_by_category": self.plot_recall_by_category(report),
            "latency_distribution": self.plot_latency_distribution(report),
            "failure_count": self.plot_failure_count_by_category(report),
            "overall_accuracy": self.plot_overall_accuracy(report),
        }
