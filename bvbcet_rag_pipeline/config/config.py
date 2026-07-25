"""Main Configuration module for BVBCET RAG Ingestion Pipeline Phase 2."""

from dataclasses import dataclass
from pathlib import Path

from config.constants import DEFAULT_MAX_PAGES, DEFAULT_TIMEOUT, USER_AGENT

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
MARKDOWN_DIR = KNOWLEDGE_BASE_DIR / "markdown"
PDF_DIR = KNOWLEDGE_BASE_DIR / "pdf"
METADATA_DIR = KNOWLEDGE_BASE_DIR / "metadata"
LOGS_DIR = KNOWLEDGE_BASE_DIR / "logs"

STATE_FILE = LOGS_DIR / "state.json"
METADATA_FILE = METADATA_DIR / "metadata.json"
CRAWL_LOG_FILE = LOGS_DIR / "crawl.log"
FAILED_PAGES_LOG = LOGS_DIR / "failed_pages.log"
PDF_DOWNLOAD_LOG = LOGS_DIR / "pdf_download.log"
STATISTICS_FILE = LOGS_DIR / "statistics.json"


@dataclass
class PipelineConfig:
    """Dataclass storing pipeline runtime parameters."""

    start_url: str = "https://www.kletech.ac.in/hubballi/"
    allowed_domains: set[str] = None
    max_pages: int = DEFAULT_MAX_PAGES
    max_depth: int = 5
    request_timeout: int = DEFAULT_TIMEOUT
    crawl_delay: float = 0.5
    user_agent: str = USER_AGENT
    headless: bool = True
    respect_robots_txt: bool = True

    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = {"kletech.ac.in", "www.kletech.ac.in", "bvb.edu", "www.bvb.edu"}
