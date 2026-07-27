"""URL Normalizer module for the crawler package."""

from utils.url_utils import normalize_url


class URLNormalizer:
    """Wrapper class for URL canonicalization and parameter stripping."""

    @staticmethod
    def normalize(url: str) -> str:
        """Canonicalize URL string."""
        return normalize_url(url)
