"""Duplicate Content Manager for MD5 hash tracking and page deduplication."""

from utils.helpers import compute_md5


class DuplicateManager:
    """Tracks MD5 hashes of document content to prevent duplicate exports."""

    def __init__(self) -> None:
        self.seen_hashes: set[str] = set()

    def is_duplicate(self, content: str | bytes) -> bool:
        """Check if content hash has already been registered."""
        content_hash = compute_md5(content)
        if content_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(content_hash)
        return False

    def add_hash(self, content_hash: str) -> None:
        """Register an existing content hash."""
        self.seen_hashes.add(content_hash)
