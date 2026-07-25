#!/usr/bin/env python3
"""BVBCET / KLE Tech Campus Website Ingestion Pipeline — Entry Point.

Usage:
    python main.py                 # Run ingestion (supports state resume)
    python main.py --fresh         # Start clean ingestion run
    python main.py --max-pages 500 # Set maximum pages limit
"""

import argparse
import shutil
import sys
from pathlib import Path

import config
from scraper.crawler import AsyncWebsiteCrawler
from scraper.logger import setup_logger
from scraper.metadata_logger import MetadataLogger
from scraper.pdf_converter import PDFConverterPipeline
from scraper.state_manager import StateManager

logger = setup_logger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="BVBCET / KLE Tech Website Ingestion Pipeline for RAG")
    parser.add_argument("--fresh", action="store_true", help="Clear prior state and restart fresh ingestion run")
    parser.add_argument("--max-pages", type=int, default=config.MAX_PAGES, help="Maximum number of pages to crawl")
    parser.add_argument("--skip-pdfs", action="store_true", help="Skip downloading and converting PDF files")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.fresh:
        logger.info("Fresh flag passed. Clearing previous state and metadata...")
        for target_file in [config.STATE_FILE, config.METADATA_FILE, config.FAILED_PAGES_LOG, config.PDF_DOWNLOAD_LOG, config.STATISTICS_FILE]:
            if target_file.exists():
                try:
                    target_file.unlink()
                except Exception:
                    pass

    config.MAX_PAGES = args.max_pages

    logger.info("Initializing BVBCET / KLE Tech Knowledge Base Ingestion Pipeline...")
    logger.info(f"Target Website Root: {config.START_URL}")

    state_mgr = StateManager()
    metadata_logger = MetadataLogger()
    pdf_pipeline = PDFConverterPipeline()

    crawler = AsyncWebsiteCrawler(
        start_url=config.START_URL,
        allowed_domains=config.ALLOWED_DOMAINS,
        state_manager=state_mgr,
        metadata_logger=metadata_logger,
        pdf_pipeline=pdf_pipeline,
    )

    if args.skip_pdfs:
        crawler.pdf_queue.clear()

    try:
        crawler.crawl_sync()
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user. Saving checkpoint...")
        state_mgr.save()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        state_mgr.save()
        sys.exit(1)

    logger.info("==========================================")
    logger.info("INGESTION PIPELINE COMPLETED")
    logger.info(f"Pages Crawled: {state_mgr.stats['pages_crawled']}")
    logger.info(f"Pages Skipped: {state_mgr.stats['pages_skipped']}")
    logger.info(f"Pages Failed: {state_mgr.stats['pages_failed']}")
    logger.info(f"PDFs Downloaded: {state_mgr.stats['pdfs_downloaded']}")
    logger.info(f"Markdown Files Generated: {state_mgr.stats['markdown_generated']}")
    logger.info(f"Duplicates Removed: {state_mgr.stats['duplicate_pages_removed']}")
    logger.info("==========================================")


if __name__ == "__main__":
    main()
