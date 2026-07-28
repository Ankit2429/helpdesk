"""Duplicate Document Detection Component."""

import hashlib


class DuplicateDetector:
    """Tracks document hashes to detect exact content duplicates across the ingestion pipeline."""

    def __init__(self) -> None:
        self._seen_hashes: set[str] = set()

    def compute_hash(self, content: str) -> str:
        """Compute SHA256 hex digest of normalized content."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    def is_duplicate(self, content: str) -> bool:
        """Check if content has already been processed by this detector instance."""
        doc_hash = self.compute_hash(content)
        return doc_hash in self._seen_hashes

    def register(self, content: str) -> str:
        """Register document content hash and return the SHA256 string."""
        doc_hash = self.compute_hash(content)
        self._seen_hashes.add(doc_hash)
        return doc_hash

    def clear(self) -> None:
        """Reset the internal seen hash cache."""
        self._seen_hashes.clear()

    @property
    def total_seen(self) -> int:
        """Return the number of unique documents registered."""
        return len(self._seen_hashes)
