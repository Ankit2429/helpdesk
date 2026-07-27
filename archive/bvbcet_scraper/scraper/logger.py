"""Logger utility for BVBCET / KLE Tech Web Ingestion Pipeline."""

import logging
import sys
from pathlib import Path

from config import CRAWL_LOG_FILE, FAILED_PAGES_LOG, PDF_DOWNLOAD_LOG

_loggers: dict[str, logging.Logger] = {}


def setup_logger(name: str = "ingestion_pipeline") -> logging.Logger:
    """Create and configure structured logger with console and file handlers."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Crawl File Handler
    CRAWL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(CRAWL_LOG_FILE, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    _loggers[name] = logger
    return logger


def log_failed_page(url: str, reason: str) -> None:
    """Log failed pages to failed_pages.log."""
    FAILED_PAGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILED_PAGES_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{url}] Error: {reason}\n")


def log_pdf_download(url: str, status: str, local_path: str = "") -> None:
    """Log PDF download status to pdf_download.log."""
    PDF_DOWNLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PDF_DOWNLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{status}] {url} -> {local_path}\n")
