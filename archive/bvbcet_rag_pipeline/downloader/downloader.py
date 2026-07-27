"""Downloader module for saving raw HTML pages and PDF documents to disk."""

import hashlib
import logging
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


class ResourceDownloader:
    """Download and store HTML files and PDFs locally."""

    def __init__(self, html_dir: Path, pdf_dir: Path) -> None:
        self.html_dir = html_dir
        self.pdf_dir = pdf_dir

    def _get_filename(self, url: str, ext: str) -> str:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
        sanitized = "".join(c if c.isalnum() else "_" for c in url.split("/")[-1])[:30]
        return f"{sanitized}_{url_hash}.{ext}"

    def download_html(self, url: str) -> Path | None:
        """Download raw HTML content."""
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "BVBCETHelpdeskRobot/1.0"})
            if resp.status_code == 200:
                filename = self._get_filename(url, "html")
                file_path = self.html_dir / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                return file_path
        except Exception as e:
            logger.error(f"Failed to download HTML from {url}: {e}")
        return None

    def download_pdf(self, url: str) -> Path | None:
        """Download raw PDF file."""
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "BVBCETHelpdeskRobot/1.0"})
            if resp.status_code == 200:
                filename = self._get_filename(url, "pdf")
                file_path = self.pdf_dir / filename
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                return file_path
        except Exception as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
        return None
