"""General helper utility functions."""

import datetime
import hashlib
import re


def compute_md5(content: str | bytes) -> str:
    """Compute MD5 hash of text or bytes content."""
    if isinstance(content, str):
        return hashlib.md5(content.encode("utf-8")).hexdigest()
    return hashlib.md5(content).hexdigest()


def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO-8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def clean_string(text: str) -> str:
    """Strip non-printable control characters and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()
