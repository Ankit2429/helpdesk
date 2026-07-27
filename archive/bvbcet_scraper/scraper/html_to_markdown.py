"""HTML to Markdown converter stripping UI noise and extracting structured text."""

import hashlib
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def slugify_title(title: str, max_len: int = 50) -> str:
    """Convert page title to clean filename slug."""
    clean = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    slug = re.sub(r"[-\s]+", "_", clean)
    if not slug:
        slug = "untitled_page"
    return slug[:max_len]


class HTMLToMarkdownConverter:
    """Extract clean content from HTML and format as structured Markdown."""

    @staticmethod
    def extract_title(soup: BeautifulSoup, default_url: str) -> str:
        """Extract clean document title from H1 or <title> tag."""
        if soup.h1 and soup.h1.get_text().strip():
            return soup.h1.get_text().strip()
        if soup.title and soup.title.get_text().strip():
            # Strip site name suffixes like '| KLE Tech'
            raw_title = soup.title.get_text().strip()
            return raw_title.split("|")[0].split("-")[0].strip()
        path = urlparse(default_url).path.strip("/")
        return path.replace("/", "_") or "home"

    @classmethod
    def convert(cls, html_content: str, url: str) -> dict[str, str]:
        """Convert HTML string to clean Markdown document."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove unwanted boilerplate elements
        noise_selectors = [
            "nav", "header", "footer", ".navbar", ".footer", ".header",
            "#header", "#footer", ".cookie-banner", ".sidebar", ".menu",
            "script", "style", "iframe", "noscript", ".social-share",
            ".widgets", ".popup", "#cookie-consent",
        ]
        for selector in noise_selectors:
            for el in soup.select(selector):
                el.decompose()

        title = cls.extract_title(soup, url)

        # 2. Convert remaining main content container (or body) to markdown
        main_content = soup.find("main") or soup.find("article") or soup.find("div", id="content") or soup.body or soup

        # Simple, high-quality text extraction preserving structure
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"**Source URL:** {url}\n")

        for elem in main_content.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
            if elem.name.startswith("h"):
                level = "#" * int(elem.name[1])
                lines.append(f"\n{level} {elem.get_text().strip()}\n")
            elif elem.name == "p":
                text = elem.get_text().strip()
                if text:
                    lines.append(f"{text}\n")
            elif elem.name in ["ul", "ol"]:
                for li in elem.find_all("li", recursive=False):
                    li_text = li.get_text().strip()
                    if li_text:
                        lines.append(f"- {li_text}")
                lines.append("")
            elif elem.name == "table":
                # Convert table rows
                rows = elem.find_all("tr")
                for row in rows:
                    cols = [td.get_text().strip() for td in row.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")
                lines.append("")

        markdown_text = "\n".join(lines).strip()
        
        # Generate safe unique filename stem
        slug = slugify_title(title)
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:6]
        filename_stem = f"{slug}_{url_hash}"

        return {
            "title": title,
            "markdown": markdown_text,
            "filename_stem": filename_stem,
        }
