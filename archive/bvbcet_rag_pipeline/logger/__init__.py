"""Logger package initialization."""

from logger.logger import get_logger, log_failed_page, log_pdf_download_status
from logger.statistics import CrawlStatistics, StatisticsTracker

__all__ = [
    "get_logger",
    "log_failed_page",
    "log_pdf_download_status",
    "CrawlStatistics",
    "StatisticsTracker",
]
