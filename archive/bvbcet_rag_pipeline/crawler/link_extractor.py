"""Link Extractor module extracting internal pages and PDF document links."""

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from utils.url_utils import is_allowed_domain, is_excluded_url, normalize_url


class LinkExtractor:
    """Extracts internal page links and PDF document URLs from DOM elements."""

    def __init__(self, allowed_domains: set[str]) -> None:
        self.allowed_domains = allowed_domains

    def extract(self, html_content: str, base_url: str) -> tuple[set[str], set[str]]:
        """Extract (internal_page_links, pdf_document_links) from HTML content."""
        page_links: set[str] = set()
        pdf_links: set[str] = set()

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            elements = soup.find_all(["a", "iframe", "embed", "object", "area"])

            for elem in elements:
                target_url = elem.get("href") or elem.get("src") or elem.get("data") or ""
                target_url = target_url.strip()

                if not target_url or is_excluded_url(target_url):
                    continue

                full_url = normalize_url(urljoin(base_url, target_url))
                full_lower = full_url.lower()

                # PDF identification
                is_pdf = (
                    full_lower.endswith(".pdf")
                    or ".pdf?" in full_lower
                    or "/pdf/" in full_lower
                    or "viewpdf" in full_lower
                    or "download.aspx" in full_lower
                    or elem.get("download") is not None
                )

                if is_pdf and is_allowed_domain(full_url, self.allowed_domains):
                    pdf_links.add(full_url)
                elif is_allowed_domain(full_url, self.allowed_domains):
                    page_links.add(full_url)
        except Exception:
            pass

        return page_links, pdf_links
