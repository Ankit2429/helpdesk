"""Queue Manager module for managing visited, pending, and failed URL sets."""

import json
from pathlib import Path
from config.config import STATE_FILE
from logger.logger import get_logger

logger = get_logger("queue_manager")


class QueueManager:
    """Manages resumable sets of visited, pending, and failed URLs."""

    def __init__(self, state_file: Path = STATE_FILE) -> None:
        self.state_file = state_file
        self.visited_urls: set[str] = set()
        self.pending_urls: list[str] = []
        self.failed_urls: set[str] = set()
        self.pdf_visited_urls: set[str] = set()
        self.load()

    def load(self) -> None:
        """Load queue checkpoint state from disk if available."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.visited_urls = set(data.get("visited_urls", []))
                self.pending_urls = data.get("pending_urls", [])
                self.failed_urls = set(data.get("failed_urls", []))
                self.pdf_visited_urls = set(data.get("pdf_visited_urls", []))
                logger.info(f"Loaded queue state: {len(self.visited_urls)} visited, {len(self.pending_urls)} pending.")
            except Exception as e:
                logger.warning(f"Error loading queue checkpoint: {e}")

    def save(self) -> None:
        """Persist current queue state to JSON."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "visited_urls": list(self.visited_urls),
                "pending_urls": self.pending_urls,
                "failed_urls": list(self.failed_urls),
                "pdf_visited_urls": list(self.pdf_visited_urls),
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving queue checkpoint: {e}")

    def add_pending(self, url: str) -> None:
        """Add new URL to pending queue if not visited."""
        if url not in self.visited_urls and url not in self.pending_urls:
            self.pending_urls.append(url)

    def pop_pending(self) -> str | None:
        """Pop next pending URL from queue."""
        if self.pending_urls:
            return self.pending_urls.pop(0)
        return None

    def mark_visited(self, url: str) -> None:
        """Mark URL as visited."""
        self.visited_urls.add(url)
        if url in self.pending_urls:
            self.pending_urls.remove(url)
        self.save()

    def mark_failed(self, url: str) -> None:
        """Mark URL as failed."""
        self.failed_urls.add(url)
        if url in self.pending_urls:
            self.pending_urls.remove(url)
        self.save()
