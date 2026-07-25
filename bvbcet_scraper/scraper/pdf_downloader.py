"""Downloads PDFs referenced by crawled pages into RAW_PDF_DIR."""

import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

import config
from scraper.logger import get_logger

log = get_logger(__name__)


def url_to_filename(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name or "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    # Prefix with a short hash to avoid collisions between same-named PDFs
    # served from different departments/pages.
    short_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{short_hash}_{name}"


def download_pdf(url: str, session: requests.Session) -> Path | None:
    config.RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.RAW_PDF_DIR / url_to_filename(url)

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT, stream=True)
            if resp.status_code != 200:
                raise requests.RequestException(f"status {resp.status_code}")
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            log.info(f"Downloaded PDF: {url} -> {dest.name}")
            return dest
        except requests.RequestException as e:
            wait = config.RETRY_BACKOFF_BASE ** attempt
            log.warning(f"PDF download failed ({attempt}/{config.MAX_RETRIES}) {url}: {e}. "
                       f"Retrying in {wait:.1f}s")
            time.sleep(wait)

    log.error(f"Giving up downloading PDF: {url}")
    return None


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
