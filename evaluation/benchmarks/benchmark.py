"""Executable CLI Entry Point for RAG Retrieval Benchmarking Framework.

Executes the entire retrieval benchmark with a single command:
    python benchmark.py
or
    python evaluation/benchmarks/benchmark.py
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure workspace root is in sys.path
current_dir = Path(__file__).resolve().parent
workspace_root = current_dir.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from evaluation.benchmarks.retrieval_benchmark import RetrievalBenchmark
from evaluation.benchmarks.retrieval_plotter import RetrievalPlotter
from evaluation.benchmarks.retrieval_report_generator import RetrievalReportGenerator


def print_progress_bar(current: int, total: int, status_str: str, start_time: float) -> None:
    """Renders a clean CLI progress bar with elapsed and estimated remaining time."""
    bar_length = 30
    percent = float(current) / float(total) if total > 0 else 1.0
    arrow = "=" * int(round(percent * bar_length) - 1) + ">"
    spaces = " " * (bar_length - len(arrow))

    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    remaining = (total - current) / rate if rate > 0 else 0

    status_sub = status_str[:35].ljust(35)
    sys.stdout.write(
        f"\r[{arrow}{spaces}] {int(percent * 100)}% ({current}/{total}) | {status_sub} | "
        f"Elapsed: {int(elapsed)}s | ETA: {int(remaining)}s"
    )
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments for benchmark execution."""
    parser = argparse.ArgumentParser(
        description="Offline AI Campus Helpdesk Robot - RAG Retrieval Benchmarking Suite"
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="evaluation/datasets",
        help="Path to directory containing dataset JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/reports",
        help="Path to directory where evaluation reports will be saved.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Optional domain category name to benchmark (e.g. Admission, Fees, Hostel).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieval rank cut-off depth K (default: 5).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel worker threads count (default: 4).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run benchmark in fast mock adapter mode without calling active vector DB.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG level logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI execution method."""
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "=" * 65)
    print("   OFFLINE AI CAMPUS HELPDESK ROBOT - RAG RETRIEVAL BENCHMARK")
    print("=" * 65)
    print(f" Dataset Directory : {args.dataset_dir}")
    print(f" Output Directory  : {args.output_dir}")
    print(f" Top-K Cut-off     : {args.top_k}")
    print(f" Parallel Workers  : {args.workers}")
    if args.category:
        print(f" Category Filter   : {args.category}")
    if args.dry_run:
        print(" Mode              : DRY-RUN (Mock Adapter)")
    print("-" * 65 + "\n")

    # Initialize benchmark engine
    benchmark_engine = RetrievalBenchmark(
        dataset_dir=Path(args.dataset_dir),
        top_k=args.top_k,
        max_workers=args.workers,
        retriever_pipeline=None if not args.dry_run else None,
    )

    start_bench_time = time.time()

    def cb(curr: int, tot: int, status: str) -> None:
        print_progress_bar(curr, tot, status, start_bench_time)

    # Execute benchmark run
    report = benchmark_engine.run_benchmark(
        category_filter=args.category, progress_callback=cb
    )

    # Generate plots and reports
    plots_dir = Path(args.output_dir) / "plots"
    plotter = RetrievalPlotter(plots_dir=plots_dir)
    plotter.generate_all_plots(report)

    report_gen = RetrievalReportGenerator(output_dir=args.output_dir)
    report_gen.generate_all_reports(report)

    # Display console summary and decision guidance
    print("\n" + "=" * 65)
    print("               BENCHMARK RESULTS & METRICS SUMMARY")
    print("=" * 65)
    print(f" Total Queries Evaluated : {report.total_queries}")
    print(f" Overall Recall@1        : {report.overall_recall_at_1 * 100.0:.2f}%")
    print(f" Overall Recall@3        : {report.overall_recall_at_3 * 100.0:.2f}%")
    print(f" Overall Recall@5        : {report.overall_recall_at_5 * 100.0:.2f}%")
    print(f" Overall MRR             : {report.overall_mrr:.4f}")
    print(f" Success Rate (Top 5)    : {report.overall_success_rate * 100.0:.2f}%")
    print(f" Failure Count           : {report.overall_failure_count}")
    print(f" Mean / Median Latency   : {report.overall_mean_latency_ms:.2f} ms / {report.overall_median_latency_ms:.2f} ms")
    print(f" P95 Latency             : {report.overall_p95_latency_ms:.2f} ms")
    print("-" * 65)

    print("\n DECISION GUIDANCE & RETRIEVAL SUFFICIENCY INTERPRETATION:")
    print(" ---------------------------------------------------------")
    if report.overall_recall_at_1 >= 0.80 and report.overall_recall_at_5 >= 0.90:
        print(" [PASS] RETRIEVAL SUFFICIENT: Retrieval quality meets production standards!")
        print("    High Recall@1 and Recall@5 indicate correct context documents are consistently found.")
    else:
        print(" [NEEDS OPTIMIZATION] RETRIEVAL QUALITY REQUIRES ATTENTION:")
        if report.overall_recall_at_1 < 0.80:
            print("    - Recall@1 < 80%: Top-1 rank precision is sub-optimal. Tune BM25 search weights or enable cross-encoder reranking.")
        if report.overall_recall_at_5 < 0.90:
            print("    - Recall@5 < 90%: Target documents missing from context window. Adjust chunk overlap or re-index vector database.")
        if report.overall_mrr < 0.85:
            print("    - MRR < 0.8500: Search rank position needs re-ordering optimization.")

    print("\n Generated Reports & Plots:")
    print(f"  - Markdown Report : {Path(args.output_dir) / 'retrieval_report.md'}")
    print(f"  - JSON Report     : {Path(args.output_dir) / 'retrieval_report.json'}")
    print(f"  - Failed Cases    : {Path(args.output_dir) / 'failed_cases.json'}")
    print(f"  - Summary CSV     : {Path(args.output_dir) / 'summary.csv'}")
    print(f"  - Plots Directory : {plots_dir}")
    print("=" * 65 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
