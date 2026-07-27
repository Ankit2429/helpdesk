"""PDF Downloader and Multi-Tier PDF to Markdown Converter."""

import hashlib
import logging
from pathlib import Path
import requests

from config import PDF_DIR, MARKDOWN_DIR
from scraper.classifier import classify_category
from scraper.logger import setup_logger, log_pdf_download

logger = setup_logger("pdf_converter")


class PDFConverterPipeline:
    """Download PDFs and convert to Markdown using Docling with PyMuPDF/PyPDF fallbacks."""

    def __init__(self, pdf_dir: Path = PDF_DIR, markdown_dir: Path = MARKDOWN_DIR) -> None:
        self.pdf_dir = pdf_dir
        self.markdown_dir = markdown_dir
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BVBCET-KLETech-KnowledgeBaseBot/2.0"})

    def download_pdf(self, pdf_url: str) -> Path | None:
        """Download raw PDF to knowledge_base/pdf/ directory."""
        try:
            filename = pdf_url.split("/")[-1].split("?")[0]
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            
            # Sanitize filename
            filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
            local_path = self.pdf_dir / filename

            resp = self.session.get(pdf_url, timeout=25)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                log_pdf_download(pdf_url, "SUCCESS", str(local_path))
                return local_path
            else:
                log_pdf_download(pdf_url, f"HTTP_{resp.status_code}")
        except Exception as e:
            logger.error(f"Error downloading PDF {pdf_url}: {e}")
            log_pdf_download(pdf_url, f"ERROR: {e}")
        return None

    def convert_pdf_to_markdown(self, pdf_path: Path, pdf_url: str) -> tuple[str, Path | None, str]:
        """Convert PDF to Markdown using Docling -> PyMuPDF4LLM -> PyPDF fallback chain."""
        text_md = ""
        method_used = "none"

        # Tier 1: Docling
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(str(pdf_path))
            text_md = result.document.export_to_markdown()
            method_used = "docling"
        except Exception as e1:
            logger.debug(f"Docling unavailable/failed for {pdf_path}: {e1}")

        # Tier 2: PyMuPDF4LLM fallback
        if not text_md:
            try:
                import pymupdf4llm
                text_md = pymupdf4llm.to_markdown(str(pdf_path))
                method_used = "pymupdf4llm"
            except Exception as e2:
                logger.debug(f"PyMuPDF4LLM unavailable/failed for {pdf_path}: {e2}")

        # Tier 3: PyPDF fallback
        if not text_md:
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                pages = []
                for i, page in enumerate(reader.pages):
                    p_text = page.extract_text()
                    if p_text:
                        pages.append(f"## Page {i + 1}\n\n{p_text}")
                text_md = "\n\n".join(pages)
                method_used = "pypdf"
            except Exception as e3:
                logger.error(f"All PDF converters failed for {pdf_path}: {e3}")
                return "", None, "failed"

        category = classify_category(pdf_url, pdf_path.stem)
        target_dir = self.markdown_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        md_filename = f"{pdf_path.stem}.md"
        output_md_path = target_dir / md_filename

        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(f"# PDF Document: {pdf_path.stem}\n")
            f.write(f"**PDF Source:** {pdf_url}\n\n")
            f.write(text_md)

        return text_md, output_md_path, method_used
