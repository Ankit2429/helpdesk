"""
Converts a downloaded PDF to Markdown using a three-tier fallback chain:

  1. Docling       — best structure/table fidelity, handles most PDFs.
  2. PyMuPDF4LLM   — fast, good fallback for text-native PDFs Docling
                      chokes on.
  3. OCR           — last resort for scanned/image-only PDFs
                      (pytesseract + pdf2image).

Each tier is optional at the dependency level: if a library isn't
installed, that tier is skipped with a warning rather than crashing the
whole pipeline.
"""

from pathlib import Path

from scraper.logger import get_logger

log = get_logger(__name__)


def _try_docling(pdf_path: Path) -> str | None:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        log.debug("docling not installed; skipping tier 1")
        return None
    try:
        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()
        if markdown and len(markdown.strip()) > 20:
            return markdown
        log.warning(f"docling produced near-empty output for {pdf_path.name}")
        return None
    except Exception as e:
        log.warning(f"docling failed on {pdf_path.name}: {e}")
        return None


def _try_pymupdf4llm(pdf_path: Path) -> str | None:
    try:
        import pymupdf4llm
    except ImportError:
        log.debug("pymupdf4llm not installed; skipping tier 2")
        return None
    try:
        markdown = pymupdf4llm.to_markdown(str(pdf_path))
        if markdown and len(markdown.strip()) > 20:
            return markdown
        log.warning(f"pymupdf4llm produced near-empty output for {pdf_path.name}")
        return None
    except Exception as e:
        log.warning(f"pymupdf4llm failed on {pdf_path.name}: {e}")
        return None


def _try_ocr(pdf_path: Path) -> str | None:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        log.debug("pytesseract/pdf2image not installed; skipping tier 3 (OCR)")
        return None
    try:
        pages = convert_from_path(str(pdf_path), dpi=200)
        text_parts = []
        for i, page_image in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page_image)
            if text.strip():
                text_parts.append(f"## Page {i}\n\n{text.strip()}")
        if text_parts:
            return "\n\n".join(text_parts)
        log.warning(f"OCR produced no text for {pdf_path.name}")
        return None
    except Exception as e:
        log.error(f"OCR failed on {pdf_path.name}: {e}")
        return None


TIER_FUNCS = {
    "docling": _try_docling,
    "pymupdf4llm": _try_pymupdf4llm,
    "ocr": _try_ocr,
}


def convert(pdf_path: Path, order: list[str] | None = None) -> tuple[str | None, str | None]:
    """Returns (markdown_text, method_used) — method_used is None if every
    tier failed, in which case the PDF should be flagged for manual review."""
    import config
    order = order or config.PDF_CONVERSION_ORDER
    for method in order:
        func = TIER_FUNCS.get(method)
        if func is None:
            continue
        markdown = func(pdf_path)
        if markdown:
            log.info(f"Converted {pdf_path.name} via {method}")
            return markdown, method
    log.error(f"All conversion tiers failed for {pdf_path.name}; needs manual review")
    return None, None
