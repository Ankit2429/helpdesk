"""Filename Generator module for slugifying titles and appending hash suffixes."""

import re
from utils.helpers import compute_md5


class FilenameGenerator:
    """Generates clean, collision-free filename stems from page titles and URLs."""

    @staticmethod
    def generate_filename_stem(title: str, url: str, max_len: int = 45) -> str:
        """Convert title into slugified filename stem with 6-character URL hash suffix."""
        clean = re.sub(r"[^\w\s-]", "", title.lower()).strip()
        slug = re.sub(r"[-\s]+", "_", clean)
        if not slug:
            slug = "untitled"

        slug_truncated = slug[:max_len].strip("_")
        url_hash = compute_md5(url)[:6]

        return f"{slug_truncated}_{url_hash}"
