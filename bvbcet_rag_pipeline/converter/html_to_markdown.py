"""HTML to Markdown Converter stripping boilerplate and extracting clean content."""

from bs4 import BeautifulSoup
from urllib.parse import urlparse


class HTMLToMarkdownConverter:
    """Parses HTML DOM, strips navigation/footer noise, and generates clean Markdown."""

    @staticmethod
    def extract_title(soup: BeautifulSoup, fallback_url: str) -> str:
        """Extract clean document title from H1 or <title> element."""
        if soup.h1 and soup.h1.get_text().strip():
            return soup.h1.get_text().strip()
        if soup.title and soup.title.get_text().strip():
            raw = soup.title.get_text().strip()
            return raw.split("|")[0].split("-")[0].strip()
        path = urlparse(fallback_url).path.strip("/")
        return path.replace("/", "_") or "home"

    @classmethod
    def convert(cls, html_content: str, url: str) -> tuple[str, str]:
        """Convert HTML string to clean (title, markdown_text) tuple."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip navigation, header, footer, script, style, and widget noise
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
        main_body = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", id="content")
            or soup.body
            or soup
        )

        lines: list[str] = [f"# {title}\n", f"**Source URL:** {url}\n"]

        for elem in main_body.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
            if elem.name.startswith("h"):
                level = "#" * int(elem.name[1])
                lines.append(f"\n{level} {elem.get_text().strip()}\n")
            elif elem.name == "p":
                txt = elem.get_text().strip()
                if txt:
                    lines.append(f"{txt}\n")
            elif elem.name in ["ul", "ol"]:
                for li in elem.find_all("li", recursive=False):
                    li_txt = li.get_text().strip()
                    if li_txt:
                        lines.append(f"- {li_txt}")
                lines.append("")
            elif elem.name == "table":
                for row in elem.find_all("tr"):
                    cols = [td.get_text().strip() for td in row.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")
                lines.append("")

        return title, "\n".join(lines).strip()
