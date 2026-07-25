"""Web Crawler module for discovering campus URLs and PDF links."""

import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class CampusCrawler:
    """Crawler to discover internal campus pages and PDF documents."""

    def __init__(self, start_urls: list[str], allowed_domains: list[str], max_depth: int = 2) -> None:
        self.start_urls = start_urls
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.visited_urls: set[str] = set()

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL belongs to an allowed domain."""
        try:
            parsed = urlparse(url)
            return any(parsed.netloc.endswith(domain) for domain in self.allowed_domains)
        except Exception:
            return False

    def crawl((self) -> dict[str, list[str]]:
        """Perform simple BFS crawl to collect HTML and PDF URLs."""
        html_urls: set[str] = set()
        pdf_urls: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0) for url in self.start_urls]

        while queue:
            current_url, depth = queue.pop(0)
            if current_url in self.visited_urls or depth > self.max_depth:
                continue

            self.visited_urls.add(current_url)

            if current_url.lower().endswith(".pdf"):
                pdf_urls.add(current_url)
                continue

            if not self.is_allowed_url(current_url):
                continue

            html_urls.add(current_url)

            if depth < self.max_depth:
                try:
                    response = requests.get(current_url, timeout=10, headers={"User-Agent": "BVBCETHelpdeskRobot/1.0"})
                    if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
                        soup = BeautifulSoup(response.text, "html.parser")
                        for a_tag in soup.find_all("a", href=True):
                            href = a_tag["href"]
                            full_url = urljoin(current_url, href).split("#")[0]
                            if full_url and full_url not in self.visited_urls:
                                queue.append((full_url, depth + 1))
                except Exception as err:
                    logger.warning(f"Error crawling {current_url}: {err}")

        return {"html": list(html_urls), "pdf": list(pdf_urls)}
