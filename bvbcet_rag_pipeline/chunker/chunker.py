"""Production Runner for Semantic Markdown Chunking and JSONL Metadata Export.

Executes recursive file discovery, semantic chunking with tqdm progress bar,
SHA256 content deduplication, and JSONL/metadata/statistics export.

CLI Usage:
    python -m chunker.chunker --input knowledge_base/markdown --output chunks
"""

import argparse
import json
import logging
from pathlib import Path
import time
from typing import List, Optional

from tqdm import tqdm

from config.config import MARKDOWN_DIR
from chunker.semantic_chunker import Chunk, SemanticMarkdownChunker
from chunker.metadata import ChunkMetadataProcessor, ChunkRecord
from logger.logger import get_logger

logger = get_logger("chunker_runner")


class ChunkerRunner:
    """Production runner orchestrating file discovery, semantic chunking, and JSONL metadata export."""

    def __init__(
        self,
        input_dir: Path = MARKDOWN_DIR,
        output_dir: Path = Path("chunks"),
        chunk_size: int = 750,
        chunk_overlap: int = 150,
        max_tokens: int = 1000,
        stats_file: Optional[Path] = None,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_tokens = max_tokens
        self.stats_file = stats_file

        self.semantic_chunker = SemanticMarkdownChunker(
            ideal_tokens=chunk_size,
            max_tokens=max_tokens,
            overlap_tokens=chunk_overlap,
        )
        self.processor = ChunkMetadataProcessor(output_dir=output_dir)
        if stats_file:
            self.processor.statistics_path = stats_file

    def run(self) -> List[ChunkRecord]:
        """Execute semantic chunking workflow over all discovered Markdown files."""
        start_time = time.time()
        logger.info("Starting Production Chunker Runner...")
        logger.info(f"Input Directory: {self.input_dir}")
        logger.info(f"Output Directory: {self.output_dir}")

        if not self.input_dir.exists() or not self.input_dir.is_dir():
            logger.error(f"Input directory does not exist or is not a directory: {self.input_dir}")
            return []

        # Recursively discover all Markdown files
        md_files = sorted(list(self.input_dir.rglob("*.md")))
        total_files = len(md_files)
        logger.info(f"Discovered {total_files} Markdown files for processing.")

        all_chunks: List[Chunk] = []
        successful_file_count = 0

        # Progress bar using tqdm
        for md_file in tqdm(md_files, desc="Chunking Markdown Files", unit="file"):
            try:
                chunks = self.semantic_chunker.process_file(md_file)
                if chunks:
                    all_chunks.extend(chunks)
                successful_file_count += 1
            except Exception as err:
                logger.error(f"Error processing file {md_file}: {err}")
                continue

        # Process metadata, deduplicate, and export JSONL storage & statistics
        records = self.processor.process_chunks(
            chunks=all_chunks,
            markdown_files_processed=successful_file_count,
        )

        duplicates_count = len(all_chunks) - len(records)
        elapsed_time = round(time.time() - start_time, 2)

        self.print_summary(
            files_processed=successful_file_count,
            chunks_generated=len(records),
            duplicates_removed=duplicates_count,
            execution_time=elapsed_time,
            output_dir=self.output_dir,
        )

        return records

    @staticmethod
    def print_summary(
        files_processed: int,
        chunks_generated: int,
        duplicates_removed: int,
        execution_time: float,
        output_dir: Path,
    ) -> None:
        """Print clean human-readable execution summary."""
        print("\n" + "=" * 50)
        print("SEMANTIC CHUNKER RUNNER SUMMARY")
        print("=" * 50)
        print(f"Markdown Files Processed : {files_processed}")
        print(f"Chunks Generated         : {chunks_generated}")
        print(f"Duplicates Removed       : {duplicates_removed}")
        print(f"Execution Time           : {execution_time}s")
        print(f"Output Directory         : {output_dir.resolve()}")
        print("=" * 50 + "\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for chunker runner."""
    parser = argparse.ArgumentParser(description="Production Semantic Markdown Chunker Runner CLI")
    parser.add_argument("-i", "--input", type=Path, default=MARKDOWN_DIR, help="Input directory containing Markdown files")
    parser.add_argument("-o", "--output", type=Path, default=Path("chunks"), help="Output directory for chunks JSONL and metrics")
    parser.add_argument("--chunk-size", type=int, default=750, help="Ideal chunk size in tokens (default: 750)")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap size in tokens (default: 150)")
    parser.add_argument("--stats", type=Path, default=None, help="Custom path for output statistics JSON file")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python -m chunker.chunker."""
    args = parse_args()
    runner = ChunkerRunner(
        input_dir=args.input,
        output_dir=args.output,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        stats_file=args.stats,
    )
    runner.run()


if __name__ == "__main__":
    main()
