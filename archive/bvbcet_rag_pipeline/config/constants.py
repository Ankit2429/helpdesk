"""Global constants for BVBCET RAG Pipeline Phase 2."""

USER_AGENT: str = (
    "BVBCET-KLETech-KnowledgeBaseBot/2.0 "
    "(+offline AI campus helpdesk RAG pipeline; respects robots.txt)"
)

DEFAULT_TIMEOUT: int = 25
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_BACKOFF: float = 1.5
DEFAULT_MAX_PAGES: int = 3000

# Excluded URL patterns
EXCLUDED_PATTERNS: list[str] = [
    "wp-login", "wp-admin", "?share=", "action=login", "mailto:", "tel:",
    "javascript:", "#", "facebook.com", "twitter.com", "instagram.com",
    "linkedin.com", "youtube.com", "google.com/maps", "maps.google",
    "pinterest.com", "whatsapp.com",
]

# Tracking query parameters to strip during normalization
TRACKING_PARAMS: set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "amp",
}

# Supported PDF extensions and MIME types
PDF_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
}
