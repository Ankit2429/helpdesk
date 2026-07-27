"""Metadata Writer module managing metadata.json storage."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.config import METADATA_FILE
from metadata.metadata_generator import PageMetadata


class MetadataWriter:
    """Manages metadata loading, upserting, and JSON file output."""

    def __init__(self, metadata_file: Path = METADATA_FILE) -> None:
        self.metadata_file = metadata_file
        self.records: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load metadata array from disk if present."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []

    def add_metadata(self, meta: PageMetadata) -> None:
        """Upsert metadata record and save JSON."""
        meta_dict = asdict(meta)
        self.records = [r for r in self.records if r.get("url") != meta.url]
        self.records.append(meta_dict)
        self.save()

    def save(self) -> None:
        """Write records to metadata.json."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2)
        except Exception:
            pass
