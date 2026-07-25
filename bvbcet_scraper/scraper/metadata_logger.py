"""Metadata Logger module tracking document properties and persisting metadata.json."""

import datetime
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config import METADATA_FILE
from scraper.logger import setup_logger

logger = setup_logger("metadata_logger")


@dataclass
class DocumentMetadata:
    """Metadata fields for RAG document ingestion."""

    title: str
    url: str
    category: str
    crawl_time: str
    last_modified: str
    language: str
    content_type: str
    word_count: int
    pdf_source: str | None
    file_path: str


class MetadataLogger:
    """Collects and writes structured document metadata into metadata.json."""

    def __init__(self, metadata_file: Path = METADATA_FILE) -> None:
        self.metadata_file = metadata_file
        self.records: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load existing metadata JSON from disk if present."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata.json: {e}")

    def add_record(
        self,
        title: str,
        url: str,
        category: str,
        content_text: str,
        file_path: Path,
        content_type: str = "text/html",
        pdf_source: str | None = None,
        last_modified: str = "",
    ) -> DocumentMetadata:
        """Record metadata for a processed Markdown document."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        word_count = len(content_text.split())

        meta = DocumentMetadata(
            title=title,
            url=url,
            category=category,
            crawl_time=now_str,
            last_modified=last_modified or now_str,
            language="en",
            content_type=content_type,
            word_count=word_count,
            pdf_source=pdf_source,
            file_path=str(file_path),
        )

        record_dict = asdict(meta)
        
        # Remove existing record with same URL if present (upsert)
        self.records = [r for r in self.records if r.get("url") != url]
        self.records.append(record_dict)

        self.save()
        return meta

    def save(self) -> None:
        """Write all metadata records to metadata.json."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata.json: {e}")
