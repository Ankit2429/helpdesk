"""PDF to Markdown converter with multi-tier fallback (Docling -> PyMuPDF4LLM -> PyPDF)."""

from pathlib import Path
from logger.logger import get_logger

logger = get_logger("pdf_converter")


class PDFToMarkdownConverter:
    """Converts PDF files to Markdown using Docling, PyMuPDF4LLM, or PyPDF."""

    @staticmethod
    def convert_pdf(pdf_path: Path) -> tuple[str, str]:
        """Convert PDF to Markdown string. Returns (markdown_text, tier_used)."""
        markdown_text = ""
        tier_used = "none"

        # Tier 1: Docling
        try:
            from docling.document_converter import DocumentConverter
            dc = DocumentConverter()
            res = dc.convert(str(pdf_path))
            markdown_text = res.document.export_to_markdown()
            tier_used = "docling"
        except Exception as e1:
            logger.debug(f"Docling conversion skipped/failed for {pdf_path.name}: {e1}")

        # Tier 2: PyMuPDF4LLM fallback
        if not markdown_text:
            try:
                import pymupdf4llm
                markdown_text = pymupdf4llm.to_markdown(str(pdf_path))
                tier_used = "pymupdf4llm"
            except Exception as e2:
                logger.debug(f"PyMuPDF4LLM conversion skipped/failed for {pdf_path.name}: {e2}")

        # Tier 3: PyPDF fallback
        if not markdown_text:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                pages = []
                for i, page in enumerate(reader.pages):
                    txt = page.extract_text()
                    if txt:
                        pages.append(f"## Page {i + 1}\n\n{txt}")
                markdown_text = "\n\n".join(pages)
                tier_used = "pypdf"
            except Exception as e3:
                logger.error(f"All PDF conversion tiers failed for {pdf_path.name}: {e3}")

        return markdown_text, tier_used
