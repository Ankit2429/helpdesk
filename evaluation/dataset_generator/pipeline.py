"""Pipeline Orchestrator for Automatic Evaluation Dataset Generator.

Orchestrates parsing, classification, question synthesis, answer extraction, validation,
semantic deduplication, and JSON dataset writing across Markdown documents.
"""

import argparse
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure workspace root is in sys.path when script is executed directly
current_dir = Path(__file__).resolve().parent
workspace_root = current_dir.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from evaluation.dataset_generator.classifier import CategoryClassifier
from evaluation.dataset_generator.config import GeneratorConfig
from evaluation.dataset_generator.deduplicator import SemanticDeduplicator
from evaluation.dataset_generator.question_generator import (
    GeneratedQuestionCandidate,
    QuestionGenerator,
)
from evaluation.dataset_generator.reader import MarkdownDocument, MarkdownReader
from evaluation.dataset_generator.validator import DatasetValidator
from evaluation.dataset_generator.writer import DatasetWriter

logger = logging.getLogger("dataset_generator")


class DatasetGeneratorPipeline:
    """Main pipeline orchestrator for evaluation dataset generation."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.reader = MarkdownReader(config.input_dir)
        self.classifier = CategoryClassifier(config)
        self.question_gen = QuestionGenerator(config)
        self.validator = DatasetValidator(config)
        self.deduplicator = SemanticDeduplicator(threshold=config.dedup_threshold)
        self.writer = DatasetWriter(config)

    def run(self) -> Dict[str, Any]:
        """Executes the dataset generation pipeline across all discovered Markdown files.

        Returns:
            Dictionary containing pipeline execution metrics and summary data.
        """
        start_time = time.time()
        logger.info(f"Starting Dataset Generation Pipeline on '{self.config.input_dir}'...")

        md_files = self.reader.find_all_markdown_files()

        # Fallback search if configured input_dir is empty but alternative markdown dirs exist
        if not md_files:
            fallback_dirs = [
                Path("bvbcet_rag_pipeline/knowledge_base/markdown"),
                Path("bvbcet_rag_pipeline/markdown"),
                Path("archive/bvbcet_rag_pipeline/knowledge_base/markdown"),
            ]
            for fb_dir in fallback_dirs:
                if fb_dir.exists():
                    logger.info(f"Using fallback Markdown directory: {fb_dir}")
                    self.reader = MarkdownReader(fb_dir)
                    md_files = self.reader.find_all_markdown_files()
                    if md_files:
                        break

        total_files = len(md_files)
        if total_files == 0:
            logger.warning("No markdown files found to process.")
            return {
                "total_files": 0,
                "processed_files": 0,
                "skipped_files": 0,
                "total_generated": 0,
                "total_discarded": 0,
                "total_duplicates_removed": 0,
                "category_counts": {},
            }

        processed_files = 0
        skipped_files = 0
        total_generated = 0
        total_discarded = 0
        total_duplicates_removed = 0

        # Category -> list of (GeneratedQuestionCandidate, MarkdownDocument)
        category_items: Dict[str, List[Tuple[GeneratedQuestionCandidate, MarkdownDocument]]] = defaultdict(list)

        for idx, file_path in enumerate(md_files, start=1):
            doc = self.reader.parse_file(file_path)
            if not doc:
                skipped_files += 1
                continue

            # Classify category
            category = self.classifier.classify(doc)
            doc.metadata["assigned_category"] = category

            # Generate candidate questions
            candidates = self.question_gen.generate_questions(doc)
            file_generated_count = len(candidates)
            total_generated += file_generated_count

            # Validate candidates
            valid_candidates: List[GeneratedQuestionCandidate] = []
            file_discarded_count = 0

            for cand in candidates:
                is_valid, reason = self.validator.validate_candidate(cand, doc)
                if is_valid:
                    valid_candidates.append(cand)
                else:
                    file_discarded_count += 1

            total_discarded += file_discarded_count

            # Deduplicate candidates within this file
            unique_candidates, file_dups_removed = self.deduplicator.deduplicate(valid_candidates)
            total_duplicates_removed += file_dups_removed

            # Accumulate category items
            for cand in unique_candidates:
                category_items[category].append((cand, doc))

            processed_files += 1

            # Progress log per file
            logger.info(
                f"[{idx}/{total_files}] Processed '{doc.filename}' | Category: '{category}' | "
                f"Generated: {file_generated_count} | Valid: {len(unique_candidates)} | "
                f"Discarded: {file_discarded_count} | Duplicates: {file_dups_removed}"
            )

        # Write/Merge datasets by category
        category_written_counts: Dict[str, int] = {}
        for category, items in category_items.items():
            seen_q = set()
            dedup_items = []
            cat_dups = 0
            for cand, doc in items:
                q_norm = cand.question.strip().lower()
                if q_norm in seen_q:
                    cat_dups += 1
                else:
                    seen_q.add(q_norm)
                    dedup_items.append((cand, doc))
            total_duplicates_removed += cat_dups

            count_written = self.writer.write_records(category, dedup_items)
            category_written_counts[category] = count_written

        elapsed = time.time() - start_time
        avg_q_per_doc = (sum(category_written_counts.values()) / float(processed_files)) if processed_files > 0 else 0.0

        summary = {
            "total_files": total_files,
            "processed_files": processed_files,
            "skipped_files": skipped_files,
            "total_generated": total_generated,
            "total_discarded": total_discarded,
            "total_duplicates_removed": total_duplicates_removed,
            "total_final_dataset_size": sum(category_written_counts.values()),
            "category_counts": category_written_counts,
            "average_questions_per_doc": avg_q_per_doc,
            "elapsed_seconds": elapsed,
        }

        self.print_final_report(summary)
        return summary

    def print_final_report(self, summary: Dict[str, Any]) -> None:
        """Prints formatted summary report to standard output."""
        print("\n" + "=" * 65)
        print("     AUTOMATIC EVALUATION DATASET GENERATION FINAL REPORT")
        print("=" * 65)
        print(f" Total Markdown Files Processed : {summary['processed_files']} / {summary['total_files']}")
        print(f" Skipped Files                 : {summary['skipped_files']}")
        print(f" Raw Questions Generated       : {summary['total_generated']}")
        print(f" Questions Discarded (Quality) : {summary['total_discarded']}")
        print(f" Duplicates Removed            : {summary['total_duplicates_removed']}")
        print(f" Total Valid Dataset Size      : {summary['total_final_dataset_size']}")
        print(f" Average Questions / Document  : {summary['average_questions_per_doc']:.2f}")
        print(f" Elapsed Time                  : {summary['elapsed_seconds']:.2f} seconds")
        print("-" * 65)
        print(" Category Breakdown:")
        for cat_name, count in sorted(summary['category_counts'].items()):
            file_name = self.config.category_file_map.get(cat_name, f"{cat_name.lower()}.json")
            print(f"   - {cat_name:<15} ({file_name}): {count} records")
        print("=" * 65 + "\n")


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for dataset generator pipeline."""
    parser = argparse.ArgumentParser(
        description="Automatic Evaluation Dataset Generator for RAG Benchmarking"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/processed_docs",
        help="Path to processed Markdown knowledge base directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/datasets",
        help="Path to output datasets directory containing category JSON files.",
    )
    parser.add_argument(
        "--min-questions",
        type=int,
        default=5,
        help="Minimum questions to generate per document (default: 5).",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=20,
        help="Maximum questions to generate per document (default: 20).",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=float,
        default=0.85,
        help="Similarity threshold ratio for deduplication (default: 0.85).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing JSON dataset files instead of appending.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG level logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = GeneratorConfig(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        min_questions_per_doc=args.min_questions,
        max_questions_per_doc=args.max_questions,
        dedup_threshold=args.dedup_threshold,
        overwrite_existing=args.overwrite,
        verbose=args.verbose,
    )

    pipeline = DatasetGeneratorPipeline(config)
    pipeline.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
