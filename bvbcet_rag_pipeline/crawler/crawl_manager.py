"""Crawl Manager orchestrator coordinating web crawling and document ingestion."""

from config.config import PipelineConfig
from converter.html_to_markdown import HTMLToMarkdownConverter
from converter.markdown_writer import MarkdownWriter
from converter.pdf_to_markdown import PDFToMarkdownConverter
from crawler.crawler import WebPageCrawler
from crawler.link_extractor import LinkExtractor
from crawler.page_classifier import PageClassifier
from crawler.queue_manager import QueueManager
from crawler.robots_handler import RobotsHandler
from crawler.sitemap_parser import SitemapParser
from downloader.download_manager import DownloadManager
from logger.logger import get_logger
from logger.statistics import StatisticsTracker
from metadata.metadata_generator import MetadataGenerator
from metadata.metadata_writer import MetadataWriter
from storage.duplicate_manager import DuplicateManager
from storage.filename_generator import FilenameGenerator
from storage.folder_manager import FolderManager
from utils.url_utils import normalize_url

logger = get_logger("crawl_manager")


class CrawlManager:
    """High-level Crawl Manager orchestrating the full ingestion pipeline."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        FolderManager.initialize_structure()

        self.queue = QueueManager()
        self.stats = StatisticsTracker()
        self.crawler = WebPageCrawler(config)
        self.link_extractor = LinkExtractor(config.allowed_domains)
        self.download_mgr = DownloadManager()
        self.dup_mgr = DuplicateManager()
        self.metadata_writer = MetadataWriter()
        self.robots_handler = RobotsHandler(config.user_agent)

        if config.respect_robots_txt:
            self.robots_handler.fetch_robots(config.start_url)

        # Bootstrap seed queue
        if not self.queue.pending_urls and not self.queue.visited_urls:
            start_norm = normalize_url(config.start_url)
            self.queue.add_pending(start_norm)

            # Discover sitemap links if available
            sitemap_urls = SitemapParser.parse_sitemap(config.start_url)
            for s_url in sitemap_urls:
                norm_s = normalize_url(s_url)
                self.queue.add_pending(norm_s)

            self.stats.inc_discovered(len(self.queue.pending_urls))

    def process_pdf(self, pdf_url: str) -> None:
        """Download and convert PDF immediately."""
        if pdf_url in self.queue.pdf_visited_urls:
            return

        self.queue.pdf_visited_urls.add(pdf_url)
        logger.info(f"[PDF DISCOVERED] Downloading & converting: {pdf_url}")

        pdf_path = self.download_mgr.download_pdf(pdf_url)
        if pdf_path:
            self.stats.inc_pdf_downloaded()
            text_md, method = PDFToMarkdownConverter.convert_pdf(pdf_path)

            if text_md:
                category = PageClassifier.classify(pdf_url, pdf_path.stem)
                filename_stem = FilenameGenerator.generate_filename_stem(pdf_path.stem, pdf_url)
                
                formatted_md = f"# PDF Document: {pdf_path.stem}\n**PDF Source:** {pdf_url}\n\n{text_md}"
                md_path = MarkdownWriter.write_markdown(category, filename_stem, formatted_md)
                
                self.stats.inc_markdown_generated()

                meta = MetadataGenerator.create_metadata(
                    title=pdf_path.stem,
                    url=pdf_url,
                    category=category,
                    content_text=formatted_md,
                    file_path=md_path,
                    content_type="application/pdf",
                    pdf_source=pdf_url,
                )
                self.metadata_writer.add_metadata(meta)
                logger.info(f"[PDF PROCESSED] Saved [{category}] -> {md_path.name}")

    def run(self) -> None:
        """Execute main crawl loop."""
        logger.info(f"Starting crawl run. Target: {self.config.start_url}")

        while self.queue.pending_urls and len(self.queue.visited_urls) < self.config.max_pages:
            url = self.queue.pop_pending()

            if not url or url in self.queue.visited_urls:
                self.stats.inc_skipped()
                continue

            if self.config.respect_robots_txt and not self.robots_handler.is_allowed(url):
                logger.info(f"Skipping {url} (blocked by robots.txt)")
                self.stats.inc_skipped()
                continue

            logger.info(f"Crawling [{len(self.queue.visited_urls) + 1}/{self.config.max_pages}]: {url}")
            html, is_pdf = self.crawler.fetch_page(url)

            if is_pdf:
                self.process_pdf(url)
                continue

            if html:
                self.queue.mark_visited(url)
                self.stats.inc_crawled()

                # Process HTML content
                title, markdown_text = HTMLToMarkdownConverter.convert(html, url)
                
                if markdown_text.strip():
                    if self.dup_mgr.is_duplicate(markdown_text):
                        self.stats.inc_duplicates_removed()
                        logger.info(f"Duplicate content skipped for {url}")
                    else:
                        category = PageClassifier.classify(url, title)
                        filename_stem = FilenameGenerator.generate_filename_stem(title, url)
                        md_path = MarkdownWriter.write_markdown(category, filename_stem, markdown_text)
                        
                        self.stats.inc_markdown_generated()

                        meta = MetadataGenerator.create_metadata(
                            title=title,
                            url=url,
                            category=category,
                            content_text=markdown_text,
                            file_path=md_path,
                            content_type="text/html",
                        )
                        self.metadata_writer.add_metadata(meta)
                        logger.info(f"Saved [{category}] -> {md_path.name}")

                # Extract sub-links
                page_links, pdf_links = self.link_extractor.extract(html, url)
                self.stats.inc_discovered(len(page_links) + len(pdf_links))

                # Process discovered PDFs immediately
                for pdf_u in pdf_links:
                    self.process_pdf(pdf_u)

                # Queue discovered page URLs
                for page_u in page_links:
                    self.queue.add_pending(page_u)
            else:
                self.queue.mark_failed(url)
                self.stats.inc_failed()

        logger.info("Crawl run finished successfully.")
