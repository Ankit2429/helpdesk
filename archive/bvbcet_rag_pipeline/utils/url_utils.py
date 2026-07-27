"""URL normalization, domain validation, and parameter stripping utilities."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from config.constants import EXCLUDED_PATTERNS, TRACKING_PARAMS


def normalize_url(url: str) -> str:
    """Canonicalize URL by stripping tracking params, fragments, and normalizing scheme/host."""
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove trailing slash from path unless root
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Strip tracking parameters from query string
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
        }
        clean_query = urlencode(filtered_params, doseq=True)

        # Reconstruct canonical URL (strip fragment)
        return urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
    except Exception:
        return url


def is_allowed_domain(url: str, allowed_domains: set[str]) -> bool:
    """Check if URL belongs to one of the allowed target domains."""
    try:
        domain = urlparse(url.lower()).netloc
        return any(domain.endswith(allowed) for allowed in allowed_domains)
    except Exception:
        return False


def is_excluded_url(url: str) -> bool:
    """Check if URL matches excluded social platforms or invalid schemes."""
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in EXCLUDED_PATTERNS)
