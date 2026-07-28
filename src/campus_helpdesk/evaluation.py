"""CLI entry point for running automated RAG benchmark evaluation suite."""

import logging
import sys
from pathlib import Path

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.evaluation.runner import EvaluationRunner
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluation")


def main() -> None:
    """Execute complete automated RAG evaluation benchmark."""
    logger.info("Initializing production RAG pipeline for evaluation benchmark...")
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)

    dataset_path = Path("evaluation/questions.yaml")
    output_dir = Path("evaluation/results")

    logger.info("Running evaluation benchmark using dataset: %s", dataset_path)
    runner = EvaluationRunner(pipeline, dataset_path=dataset_path, output_dir=output_dir)
    report = runner.run_evaluation()

    print("\n=======================================================================")
    print("           RAG EVALUATION BENCHMARK COMPLETE")
    print("=======================================================================")
    print(f"Total Questions Evaluated : {report['total_questions']}")
    print(f"Overall RAG Quality Score : {report['overall_score']}%")
    print(f"Overall Recall@5          : {report['overall_recall_at_5']:.2%}")
    print(f"Overall Recall@10         : {report['overall_recall_at_10']:.2%}")
    print(f"Mean Reciprocal Rank (MRR): {report['overall_mrr']:.4f}")
    print(f"Keyword Coverage          : {report['overall_keyword_coverage']:.2%}")
    print(f"Average Retrieval Latency : {report['average_retrieval_latency_ms']} ms")
    print("=======================================================================")
    print("\nPer-Category Breakdown:")
    for cat, cstat in report["per_category_accuracy"].items():
        print(f"  - {cat:<15}: {cstat['accuracy_score']}% (Recall@5: {cstat['recall_at_5']:.2%}, MRR: {cstat['mrr']:.4f})")
    print("\nFull reports saved to:")
    print(f"  - {output_dir / 'summary.json'}")
    print(f"  - {output_dir / 'summary.md'}")
    print("=======================================================================\n")


if __name__ == "__main__":
    main()
