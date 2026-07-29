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

    import time
    start_time = time.perf_counter()
    logger.info("\n=======================================================================")
    logger.info("           RAG EVALUATION BENCHMARK COMPLETE")
    logger.info("=======================================================================")
    logger.info("Total Questions Evaluated : %s", report['total_questions'])
    logger.info("Overall RAG Quality Score : %s%%", report['overall_score'])
    logger.info("Overall Recall@5          : %.2f%%", report['overall_recall_at_5'] * 100)
    logger.info("Overall Recall@10         : %.2f%%", report['overall_recall_at_10'] * 100)
    logger.info("Mean Reciprocal Rank (MRR): %.4f", report['overall_mrr'])
    logger.info("Keyword Coverage          : %.2f%%", report['overall_keyword_coverage'] * 100)
    logger.info("Average Retrieval Latency : %s ms", report['average_retrieval_latency_ms'])
    logger.info("=======================================================================")
    logger.info("\nPer-Category Breakdown:")
    for cat, cstat in report["per_category_accuracy"].items():
        logger.info("  - %15s: %s%% (Recall@5: %.2f%%, MRR: %.4f)", cat, cstat['accuracy_score'], cstat['recall_at_5'] * 100, cstat['mrr'])
    logger.info("\nFull reports saved to:")
    logger.info("  - %s", output_dir / 'summary.json')
    logger.info("  - %s", output_dir / 'summary.md')
    logger.info("=======================================================================\n")
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info("Evaluation completed in %.2f ms", elapsed_ms)


if __name__ == "__main__":
    main()
