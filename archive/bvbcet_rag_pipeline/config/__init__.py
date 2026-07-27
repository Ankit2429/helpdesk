"""Config package initialization."""

from config.categories import CATEGORIES, CATEGORY_RULES
from config.config import (
    BASE_DIR,
    CRAWL_LOG_FILE,
    FAILED_PAGES_LOG,
    KNOWLEDGE_BASE_DIR,
    LOGS_DIR,
    MARKDOWN_DIR,
    METADATA_DIR,
    METADATA_FILE,
    PDF_DIR,
    PDF_DOWNLOAD_LOG,
    STATE_FILE,
    STATISTICS_FILE,
    PipelineConfig,
)
from config.constants import EXCLUDED_PATTERNS, TRACKING_PARAMS, USER_AGENT

__all__ = [
    "BASE_DIR",
    "KNOWLEDGE_BASE_DIR",
    "MARKDOWN_DIR",
    "PDF_DIR",
    "METADATA_DIR",
    "LOGS_DIR",
    "STATE_FILE",
    "METADATA_FILE",
    "CRAWL_LOG_FILE",
    "FAILED_PAGES_LOG",
    "PDF_DOWNLOAD_LOG",
    "STATISTICS_FILE",
    "PipelineConfig",
    "CATEGORIES",
    "CATEGORY_RULES",
    "USER_AGENT",
    "EXCLUDED_PATTERNS",
    "TRACKING_PARAMS",
]
