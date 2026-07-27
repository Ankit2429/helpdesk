"""Page Classifier module for determining page category folder."""

from urllib.parse import urlparse
from config.categories import CATEGORIES, CATEGORY_RULES


class PageClassifier:
    """Classifies document URLs and titles into target categories."""

    @staticmethod
    def classify(url: str, title: str = "") -> str:
        """Classify URL and title into target category."""
        target_str = f"{url.lower()} {title.lower()}"
        parsed_path = urlparse(url.lower()).path

        for keywords, category in CATEGORY_RULES:
            if any(kw in target_str or kw in parsed_path for kw in keywords):
                if category in CATEGORIES:
                    return category

        return "miscellaneous"
