"""Category Classifier for mapping page URLs and titles to target Markdown directories."""

from urllib.parse import urlparse
from config import CATEGORY_RULES, CATEGORIES


def classify_category(url: str, title: str = "") -> str:
    """Classify URL and title into one of the standard categories."""
    target_str = f"{url.lower()} {title.lower()}"
    parsed_path = urlparse(url.lower()).path

    # Check keyword rules sequentially
    for keywords, category in CATEGORY_RULES:
        if any(kw in target_str or kw in parsed_path for kw in keywords):
            if category in CATEGORIES:
                return category

    return "miscellaneous"
