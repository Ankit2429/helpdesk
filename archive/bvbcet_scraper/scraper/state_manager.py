"""State Manager for state checkpointing, resume support, and statistics logging."""

import hashlib
import json
from pathlib import Path
from typing import Any

from config import STATE_FILE, STATISTICS_FILE
from scraper.logger import setup_logger

logger = setup_logger("state_manager")


class StateManager:
    """Manages crawl checkpointing, deduplication hashes, and live pipeline statistics."""

    def __init__(self, state_file: Path = STATE_FILE) -> None:
        self.state_file = state_file
        self.visited_urls: set[str] = set()
        self.pending_urls: set[str] = set()
        self.failed_urls: set[str] = set()
        self.content_hashes: set[str] = set()
        self.pdf_hashes: set[str] = set()
        self.stats: dict[str, int] = {
            "pages_crawled": 0,
            "pages_skipped": 0,
            "pages_failed": 0,
            "pdfs_downloaded": 0,
            "markdown_generated": 0,
            "duplicate_pages_removed": 0,
        }
        self.load()

    def load(self) -> None:
        """Load persistent state checkpoint from disk if present."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.visited_urls = set(data.get("visited_urls", []))
                self.pending_urls = set(data.get("pending_urls", []))
                self.failed_urls = set(data.get("failed_urls", []))
                self.content_hashes = set(data.get("content_hashes", []))
                self.pdf_hashes = set(data.get("pdf_hashes", []))
                self.stats = data.get("stats", self.stats)
                logger.info(f"Loaded state checkpoint: {len(self.visited_urls)} visited, {len(self.pending_urls)} pending.")
            except Exception as err:
                logger.warning(f"Could not load checkpoint state: {err}")

    def save(self) -> None:
        """Persist state checkpoint and statistics JSON to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "visited_urls": list(self.visited_urls),
                "pending_urls": list(self.pending_urls),
                "failed_urls": list(self.failed_urls),
                "content_hashes": list(self.content_hashes),
                "pdf_hashes": list(self.pdf_hashes),
                "stats": self.stats,
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            with open(STATISTICS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as err:
            logger.error(f"Error saving state checkpoint: {err}")

    @staticmethod
    def compute_hash(content: str | bytes) -> str:
        """Compute MD5 hash of text or binary content."""
        if isinstance(content, str):
            return hashlib.md5(content.encode("utf-8")).hexdigest()
        return hashlib.md5(content).hexdigest()

    def is_duplicate_content(self, content_hash: str) -> bool:
        """Check if content hash already exists."""
        if content_hash in self.content_hashes:
            self.stats["duplicate_pages_removed"] += 1
            return True
        self.content_hashes.add(content_hash)
        return False

    def record_visit(self, url: str) -> None:
        """Record successful URL visit."""
        self.visited_urls.add(url)
        self.pending_urls.discard(url)
        self.stats["pages_crawled"] += 1
        self.save()

    def record_failure(self, url: str) -> None:
        """Record failed URL."""
        self.failed_urls.add(url)
        self.pending_urls.discard(url)
        self.stats["pages_failed"] += 1
        self.save()
