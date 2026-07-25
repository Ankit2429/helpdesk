"""Document Converter module converting HTML & PDF documents to Markdown."""

import logging
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DocumentConverter:
    """Convert local HTML and PDF assets to structured Markdown text."""

    def __init__(self, output_markdown_dir: Path) -> None:
        self.output_markdown_dir = output_markdown_dir

    def convert_html_to_markdown(self, html_path: Path) -> Path | None:
        """Extract readable text from HTML file and save as Markdown."""
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            # Strip script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.extract()

            text = soup.get_text(separator="\n\n")
            markdown_filename = html_path.stem + ".md"
            output_path = self.output_markdown_dir / markdown_filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# Document: {html_path.stem}\n\n{text}")

            return output_path
        except Exception as e:
            logger.error(f"Error converting HTML {html_path}: {e}")
            return None

    def convert_pdf_to_markdown(self, pdf_path: Path) -> Path | None:
        """Extract text from PDF using pypdf and save as Markdown."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(f"## Page {i + 1}\n\n{text}")

            full_md = f"# PDF Document: {pdf_path.stem}\n\n" + "\n\n".join(pages_text)
            markdown_filename = pdf_path.stem + ".md"
            output_path = self.output_markdown_dir / markdown_filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_md)

            return output_path
        except Exception as e:
            logger.error(f"Error converting PDF {pdf_path}: {e}")
            return None
