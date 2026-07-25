#!/usr/bin/env python3
"""Phase 2 Production-Grade Website Ingestion Pipeline Entry Point.

Usage:
    python pipeline.py                  # Run ingestion (supports state resume)
    python pipeline.py --fresh          # Start clean ingestion run
    python pipeline.py --max-pages 500  # Set maximum pages safety ceiling
"""

import argparse
import shutil
import sys

from config.config import (
    FAILED_PAGES_LOG,
    LOGS_DIR,
    METADATA_FILE,
    PDF_DOWNLOAD_LOG,
    STATE_FILE,
    STATISTICS_FILE,
    PipelineConfig,
)
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
    logger.info("STARTING PHASE 2 RAG INGESTION PIPELINE")
    logger.info(f"Target URL: {config.start_url}")
    logger.info(f"Max Pages Limit: {config.max_pages}")
    logger.info("==================================================")

    manager = CrawlManager(config)

    try:
        manager.run()
    except KeyboardInterrupt:
        logger.warning("Pipeline execution interrupted by user. State checkpoint saved.")
        manager.queue.save()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        manager.queue.save()
        sys.exit(1)

    logger.info("==================================================")
    logger.info("PHASE 2 INGESTION PIPELINE COMPLETED SUCCESSFULLY")
    logger.info(f"Pages Discovered: {manager.stats.stats.pages_discovered}")
    logger.info(f"Pages Crawled: {manager.stats.stats.pages_crawled}")
    logger.info(f"Pages Skipped: {manager.stats.stats.pages_skipped}")
    logger.info(f"Pages Failed: {manager.stats.stats.pages_failed}")
    logger.info(f"PDFs Downloaded: {manager.stats.stats.pdfs_downloaded}")
    logger.info(f"Markdown Files Generated: {manager.stats.stats.markdown_files_generated}")
    logger.info(f"Duplicate Pages Removed: {manager.stats.stats.duplicate_pages_removed}")
    logger.info("==================================================")


if __name__ == "__main__":
    main()
