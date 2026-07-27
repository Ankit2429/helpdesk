"""Asynchronous Recursive Web Crawler using Playwright/Crawl4AI and Requests."""

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup

from config import (
    START_URL,
    ALLOWED_DOMAINS,
    SKIP_URL_PATTERNS,
    REQUEST_TIMEOUT,
    MAX_WORKERS,
    MAX_PAGES,
    MARKDOWN_DIR,
)
from scraper.classifier import classify_category
from scraper.html_to_markdown import HTMLToMarkdownConverter
from scraper.logger import setup_logger, log_failed_page
from scraper.metadata_logger import MetadataLogger
from scraper.pdf_converter import PDFConverterPipeline
from scraper.state_manager import StateManager

logger = setup_logger("crawler")


def normalize_url(url: str) -> str:
    """Canonicalize URL by lowercasing domain and stripping fragments/trailing slashes."""
    try:
        parsed = urlparse(url)
        # Strip trailing slash from path for consistency unless root
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            "",  # Strip fragment
        ))
        return normalized
    except Exception:
        return url


class AsyncWebsiteCrawler:
    """Recursive crawler traversing all internal links and processing HTML/PDF assets."""

    def __init__(
        self,
        start_url: str = START_URL,
        allowed_domains: set[str] = ALLOWED_DOMAINS,
        state_manager: StateManager | None = None,
        metadata_logger: MetadataLogger | None = None,
        pdf_pipeline: PDFConverterPipeline | None = None,
    ) -> None:
        self.start_url = normalize_url(start_url)
        self.allowed_domains = allowed_domains
        self.state = state_manager or StateManager()
        self.metadata = metadata_logger or MetadataLogger()
        self.pdf_pipeline = pdf_pipeline or PDFConverterPipeline()

        self.pending_queue: list[str] = [self.start_url]
        self.pdf_queue: set[str] = set()

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL is valid, within allowed domain, and not in skip list."""
        if not url or not url.startswith("http"):
            return False

        # Check skip patterns
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in SKIP_URL_PATTERNS):
            return False

        # Check allowed domain
        try:
            domain = urlparse(url_lower).netloc
            if not any(domain.endswith(ad) for ad in self.allowed_domains):
                return False
        except Exception:
            return False

        return True

    def extract_links(self, html_content: str, base_url: str) -> tuple[set[str], set[str]]:
        """Extract internal page links and PDF document links from HTML content."""
        page_links: set[str] = set()
        pdf_links: set[str] = set()

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Scan a, iframe, embed, object, area tags
            elements = soup.find_all(["a", "iframe", "embed", "object", "area"])
            for elem in elements:
                target_url = elem.get("href") or elem.get("src") or elem.get("data") or ""
                target_url = target_url.strip()
                
                if not target_url or target_url.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue

                full_url = normalize_url(urljoin(base_url, target_url))
                full_lower = full_url.lower()

                # Flexible PDF identification
                is_pdf = (
                    full_lower.endswith(".pdf")
                    or ".pdf?" in full_lower
                    or "/pdf/" in full_lower
                    or "viewpdf" in full_lower
                    or "download.aspx" in full_lower
                    or elem.get("download") is not None
                )

                if is_pdf and self.is_allowed_url(full_url):
                    pdf_links.add(full_url)
                elif self.is_allowed_url(full_url):
                    page_links.add(full_url)
        except Exception as e:
            logger.warning(f"Error extracting links from {base_url}: {e}")

        return page_links, pdf_links

    def process_pdf_url(self, pdf_url: str) -> None:
        """Download and convert PDF immediately when discovered."""
        if pdf_url in self.state.visited_urls:
            return
        
        self.state.visited_urls.add(pdf_url)
        logger.info(f"[PDF DISCOVERED] Downloading & converting: {pdf_url}")
        
        pdf_path = self.pdf_pipeline.download_pdf(pdf_url)
        if pdf_path:
            self.state.stats["pdfs_downloaded"] += 1
            text_md, md_path, method = self.pdf_pipeline.convert_pdf_to_markdown(pdf_path, pdf_url)
            if md_path:
                category = classify_category(pdf_url, pdf_path.stem)
                self.metadata.add_record(
                    title=pdf_path.stem,
                    url=pdf_url,
                    category=category,
                    content_text=text_md,
                    file_path=md_path,
                    content_type="application/pdf",
                    pdf_source=pdf_url,
                )
                self.state.stats["markdown_generated"] += 1
                logger.info(f"[PDF PROCESSED] Saved [{category}] -> {md_path.name}")
        self.state.save()

    def process_html_page(self, url: str, html_content: str) -> None:
        """Convert HTML page to Markdown, categorize, and save metadata."""
        conv_result = HTMLToMarkdownConverter.convert(html_content, url)
        title = conv_result["title"]
        markdown_text = conv_result["markdown"]
        filename_stem = conv_result["filename_stem"]

        if not markdown_text.strip():
            logger.warning(f"Empty content extracted from {url}, skipping.")
            return

        # Deduplication check
        content_hash = StateManager.compute_hash(markdown_text)
        if self.state.is_duplicate_content(content_hash):
            logger.info(f"Duplicate content detected for {url}, skipping output.")
            return

        category = classify_category(url, title)
        category_dir = MARKDOWN_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = category_dir / f"{filename_stem}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        self.state.stats["markdown_generated"] += 1
        
        self.metadata.add_record(
            title=title,
            url=url,
            category=category,
            content_text=markdown_text,
            file_path=output_file,
            content_type="text/html",
        )

        logger.info(f"Saved [{category}] -> {output_file.name}")

    def fetch_url(self, url: str) -> tuple[str | None, bool]:
        """Fetch URL content. Returns (text_or_none, is_pdf)."""
        try:
            resp = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "BVBCET-KLETech-KnowledgeBaseBot/2.0"},
                stream=True,
            )
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

    def crawl_sync(self) -> None:
        """Synchronous crawl loop processing pending URLs queue."""
        logger.info(f"Starting crawl from root: {self.start_url}")

        while self.pending_queue and len(self.state.visited_urls) < MAX_PAGES:
            url = self.pending_queue.pop(0)

            if url in self.state.visited_urls:
                self.state.stats["pages_skipped"] += 1
                continue

            logger.info(f"Crawling [{len(self.state.visited_urls) + 1}/{MAX_PAGES}]: {url}")
            html, is_pdf = self.fetch_url(url)

            if is_pdf:
                self.process_pdf_url(url)
                continue

            if html:
                self.state.record_visit(url)
                self.process_html_page(url, html)

                # Extract sub-links
                new_pages, new_pdfs = self.extract_links(html, url)
                
                # Process PDFs immediately!
                for pdf_url in new_pdfs:
                    if pdf_url not in self.state.visited_urls:
                        self.process_pdf_url(pdf_url)

                for page_url in new_pages:
                    if page_url not in self.state.visited_urls and page_url not in self.pending_queue:
                        self.pending_queue.append(page_url)
            else:
                self.state.record_failure(url)

        self.state.save()
        logger.info("Pipeline crawl and conversion complete.")
