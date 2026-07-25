"""Statistics Tracker for metrics collection and statistics.json output."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from config.config import STATISTICS_FILE


@dataclass
class CrawlStatistics:
    """Dataclass storing pipeline execution metrics."""

    pages_discovered: int = 0
    pages_crawled: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    pdfs_downloaded: int = 0
    markdown_files_generated: int = 0
    duplicate_pages_removed: int = 0


class StatisticsTracker:
    """Tracks live pipeline metrics and persists statistics.json."""

    def __init__(self, stats_file: Path = STATISTICS_FILE) -> None:
        self.stats_file = stats_file
        self.stats = CrawlStatistics()
        self.load()

    def load(self) -> None:
        """Load existing statistics from disk if present."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.stats = CrawlStatistics(**data)
            except Exception:
                pass

    def save(self) -> None:
        """Persist current statistics to statistics.json."""
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self.stats), f, indent=2)
        except Exception:
            pass

    def inc_discovered(self, count: int = 1) -> None:
        self.stats.pages_discovered += count
        self.save()

    def inc_crawled(self) -> None:
        self.stats.pages_crawled += 1
        self.save()

    def inc_skipped(self) -> None:
        self.stats.pages_skipped += 1
        self.save()

    def inc_failed(self) -> None:
        self.stats.pages_failed += 1
        self.save()

    def inc_pdf_downloaded(self) -> None:
        self.stats.pdfs_downloaded += 1
        self.save()

    def inc_markdown_generated(self) -> None:
        self.stats.markdown_files_generated += 1
        self.save()

    def inc_duplicates_removed(self) -> None:
        self.stats.duplicate_pages_removed += 1
        self.save()
