"""Async/Sync Web Crawler module fetching HTML content."""

import requests
from config.config import PipelineConfig
from logger.logger import get_logger, log_failed_page

logger = get_logger("crawler")


class WebPageCrawler:
    """Handles fetching web page HTML payloads over HTTP."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    def fetch_page(self, url: str) -> tuple[str | None, bool]:
        """Fetch URL content. Returns (html_string_or_none, is_pdf_flag)."""
        try:
            resp = self.session.get(url, timeout=self.config.request_timeout, stream=True)
            content_type = resp.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                return None, True

            if resp.status_code == 200 and "text/html" in content_type:
                return resp.text, False
            else:
                log_failed_page(url, f"HTTP Status {resp.status_code}")
        except Exception as err:
            log_failed_page(url, str(err))
            logger.warning(f"Error fetching {url}: {err}")
        return None, False
