#!/usr/bin/env python3
"""Phase 2 Production-Grade Website Ingestion & Semantic Chunking Pipeline Entry Point.

Execution Flow:
    Crawler -> Downloader -> Markdown Generator -> Semantic Chunker

Usage:
    python pipeline.py                  # Run ingestion & chunking (supports state resume)
    python pipeline.py --fresh          # Start clean ingestion run
    python pipeline.py --max-pages 500  # Set maximum pages safety ceiling
"""

import argparse
import sys
import time

from config.config import (
    FAILED_PAGES_LOG,
    KNOWLEDGE_BASE_DIR,
    LOGS_DIR,
    MARKDOWN_DIR,
    METADATA_FILE,
    PDF_DOWNLOAD_LOG,
    STATE_FILE,
    STATISTICS_FILE,
    PipelineConfig,
)
from chunker.chunker import ChunkerRunner
from crawler.crawl_manager import CrawlManager
from logger.logger import get_logger

logger = get_logger("pipeline")


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 2 BVBCET / KLE Tech RAG Ingestion Pipeline")
    parser.add_argument("--fresh", action="store_true", help="Clear prior state and restart fresh ingestion run")
    parser.add_argument("--max-pages", type=int, default=3000, help="Maximum number of pages to crawl")
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline_start_time = time.time()

    if args.fresh:
        logger.info("Fresh flag passed. Clearing previous state files...")
        for target in [STATE_FILE, METADATA_FILE, FAILED_PAGES_LOG, PDF_DOWNLOAD_LOG, STATISTICS_FILE]:
            if target.exists():
                try:
                    target.unlink()
                except Exception:
                    pass

    config = PipelineConfig(max_pages=args.max_pages)

    logger.info("==================================================")
    logger.info("STARTING RAG INGESTION & CHUNKING PIPELINE")
    logger.info(f"Target URL: {config.start_url}")
    logger.info(f"Max Pages Limit: {config.max_pages}")
    logger.info("==================================================")

    manager = CrawlManager(config)

    try:
        # Phase 1: Web Crawl, PDF Downloading, and Markdown Generation
        manager.run()

        # Phase 2: Semantic Chunking & JSONL Export
        logger.info("==================================================")
        logger.info("STARTING SEMANTIC CHUNKING PHASE")
        logger.info("==================================================")

        chunker_output_dir = KNOWLEDGE_BASE_DIR / "chunks"
        chunker_runner = ChunkerRunner(
            input_dir=MARKDOWN_DIR,
            output_dir=chunker_output_dir,
        )
        chunk_records = chunker_runner.run()

    except KeyboardInterrupt:
        logger.warning("Pipeline execution interrupted by user. State checkpoint saved.")
        manager.queue.save()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        manager.queue.save()
        sys.exit(1)

    total_processing_time = round(time.time() - pipeline_start_time, 2)
    duplicates_removed_total = (
        manager.stats.stats.duplicate_pages_removed + chunker_runner.processor.duplicates_path.exists()
    )

    logger.info("==================================================")
    logger.info("FINAL PIPELINE SUMMARY")
    logger.info("==================================================")
    logger.info(f"Pages Crawled            : {manager.stats.stats.pages_crawled}")
    logger.info(f"Markdown Files Generated : {manager.stats.stats.markdown_files_generated}")
    logger.info(f"Chunks Generated         : {len(chunk_records)}")
    logger.info(f"Duplicates Removed       : {manager.stats.stats.duplicate_pages_removed}")
    logger.info(f"Processing Time          : {total_processing_time}s")
    logger.info("==================================================")


if __name__ == "__main__":
    main()
