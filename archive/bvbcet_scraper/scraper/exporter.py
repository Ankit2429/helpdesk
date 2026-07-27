"""
Appends converted page/PDF content into the right topic markdown file under
knowledge_base/, and writes one metadata.json entry per source alongside a
combined metadata.json index at the root.

Dedup: content hashes are checked by the caller (StateManager) before this
module is invoked, so exporter.py just needs to avoid writing the exact same
section twice within a single run (e.g. a page linked from two places).
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import config
from scraper.logger import get_logger

log = get_logger(__name__)

_write_lock = threading.Lock()
_metadata_index: list[dict] = []
_written_section_hashes: set[str] = set()


def _ensure_dirs():
    config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    config.DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)
    config.PDFS_DIR.mkdir(parents=True, exist_ok=True)


def append_page(topic_file: str, title: str, url: str, markdown_body: str, content_hash: str):
    _ensure_dirs()
    dest = config.OUTPUT_ROOT / topic_file
    dest.parent.mkdir(parents=True, exist_ok=True)

    with _write_lock:
        if content_hash in _written_section_hashes:
            return
        _written_section_hashes.add(content_hash)

        section = f"## {title}\n\nSource: {url}\n\n{markdown_body}\n\n---\n\n"
        is_new_file = not dest.exists()
        with open(dest, "a", encoding="utf-8") as f:
            if is_new_file:
                f.write(f"# {dest.stem.replace('_', ' ').title()}\n\n")
            f.write(section)

        _metadata_index.append({
            "title": title,
            "source_url": url,
            "last_scraped": datetime.now(timezone.utc).isoformat(),
            "category": topic_file,
            "department": _department_from_path(topic_file),
            "pdf_source": "",
            "language": "English",
        })


def append_pdf(pdf_url: str, source_page_url: str, title: str, markdown_body: str,
                method: str, department: str = ""):
    _ensure_dirs()
    safe_name = _slugify(title or Path(pdf_url).stem) + ".md"
    dest = config.PDFS_DIR / safe_name

    with _write_lock:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"Source PDF: {pdf_url}\n\n")
            f.write(f"Linked from: {source_page_url}\n\n")
            f.write(f"Converted via: {method}\n\n---\n\n")
            f.write(markdown_body)

        _metadata_index.append({
            "title": title,
            "source_url": source_page_url,
            "last_scraped": datetime.now(timezone.utc).isoformat(),
            "category": "pdfs",
            "department": department,
            "pdf_source": pdf_url,
            "language": "English",
        })
    log.info(f"Exported PDF markdown: {dest}")


def _department_from_path(topic_file: str) -> str:
    p = Path(topic_file)
    return p.stem if p.parent.name == "departments" else ""


def _slugify(text: str) -> str:
    import re
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "_", text)[:80] or "document"


def flush_metadata():
    """Write the combined metadata.json index. Call once at the end of a run
    (or periodically) to keep it current for interrupted runs too."""
    _ensure_dirs()
    with _write_lock:
        with open(config.OUTPUT_ROOT / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(_metadata_index, f, indent=2, ensure_ascii=False)
    log.info(f"Wrote metadata.json with {len(_metadata_index)} entries")
