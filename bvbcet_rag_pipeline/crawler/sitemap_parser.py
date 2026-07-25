"""Sitemap Parser module to discover URLs from sitemap.xml."""

from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from logger.logger import get_logger

logger = get_logger("sitemap_parser")


class SitemapParser:
    """Discovers seed URLs from domain sitemaps."""

    @staticmethod
    def parse_sitemap(base_url: str) -> set[str]:
        """Fetch and extract URLs from domain sitemap.xml."""
        urls: set[str] = set()
        try:
            parsed = urlparse(base_url)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            
            resp = requests.get(sitemap_url, timeout=15, headers={"User-Agent": "BVBCET-Bot/2.0"})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                for loc in soup.find_all("loc"):
                    if loc.text and loc.text.strip():
                        urls.add(loc.text.strip())
                logger.info(f"Discovered {len(urls)} URLs from {sitemap_url}")
        except Exception as e:
            logger.debug(f"Could not parse sitemap for {base_url}: {e}")
        return urls
