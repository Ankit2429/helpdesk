"""Metadata Generator module creating structured document metadata."""

from dataclasses import asdict, dataclass
from pathlib import Path
from utils.helpers import get_iso_timestamp


@dataclass
class PageMetadata:
    """Dataclass holding document metadata for RAG ingestion."""

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


class MetadataGenerator:
    """Generates PageMetadata instances for HTML pages and PDF documents."""

    @staticmethod
    def create_metadata(
        title: str,
        url: str,
        category: str,
        content_text: str,
        file_path: Path,
        content_type: str = "text/html",
        pdf_source: str | None = None,
        last_modified: str | None = None,
    ) -> PageMetadata:
        """Construct PageMetadata dataclass instance."""
        timestamp = get_iso_timestamp()
        words = len(content_text.split())

        return PageMetadata(
            title=title,
            url=url,
            category=category,
            crawl_time=timestamp,
            last_modified=last_modified or timestamp,
            language="en",
            content_type=content_type,
            word_count=words,
            pdf_source=pdf_source,
            file_path=str(file_path),
        )
