"""HTTP response and HTML content validation module."""


def is_valid_html_response(status_code: int, content_type: str) -> bool:
    """Check if HTTP response is a valid 200 OK HTML payload."""
    if status_code != 200:
        return False
    return "text/html" in content_type.lower() or "application/xhtml" in content_type.lower()


def is_pdf_response(content_type: str, url: str) -> bool:
    """Check if response or URL corresponds to a PDF document."""
    c_lower = content_type.lower()
    u_lower = url.lower()
    return "application/pdf" in c_lower or u_lower.endswith(".pdf") or ".pdf?" in u_lower
