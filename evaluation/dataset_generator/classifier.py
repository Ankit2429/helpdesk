"""Category Classifier Module.

Automatically assigns each Markdown document to one of the 9 predefined target categories
using path heuristics, heading matching, and content keyword scoring.
"""

import logging
from typing import Dict, List

from evaluation.dataset_generator.config import GeneratorConfig
from evaluation.dataset_generator.reader import MarkdownDocument

logger = logging.getLogger(__name__)


class CategoryClassifier:
    """Classifies Markdown documents into target dataset categories."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.keyword_rules = config.category_keywords

    def classify(self, doc: MarkdownDocument) -> str:
        """Classifies a Markdown document into one of the 9 categories.

        Args:
            doc: MarkdownDocument instance.

        Returns:
            Assigned category string (e.g., 'Admission', 'Hostel', 'Misc').
        """
        scores: Dict[str, float] = {cat: 0.0 for cat in self.config.category_file_map.keys()}

        # 1. Path-based matching (High weight: 5.0)
        path_str = str(doc.path).lower()
        if "admission" in path_str or "apply" in path_str:
            scores["Admission"] += 5.0
        if "department" in path_str or "academic" in path_str or "course" in path_str:
            scores["Departments"] += 4.0
        if "hostel" in path_str or "dorm" in path_str or "residence" in path_str:
            scores["Hostel"] += 5.0
        if "fee" in path_str or "payment" in path_str or "tuition" in path_str:
            scores["Fees"] += 5.0
        if "placement" in path_str or "career" in path_str or "recruitment" in path_str:
            scores["Placement"] += 5.0
        if "transport" in path_str or "location" in path_str or "reach" in path_str or "map" in path_str:
            scores["Navigation"] += 5.0
        if "facility" in path_str or "infrastructure" in path_str or "library" in path_str:
            scores["Facilities"] += 4.0
        if "faculty" in path_str or "staff" in path_str or "professor" in path_str:
            scores["Faculty"] += 5.0

        # 2. Title and Heading matching (Medium weight: 3.0)
        title_norm = doc.title.lower()
        headings_norm = " ".join(doc.headings).lower()
        title_headings = f"{title_norm} {headings_norm}"

        for cat, keywords in self.keyword_rules.items():
            for kw in keywords:
                if kw in title_headings:
                    scores[cat] += 3.0

        # 3. Content keyword frequency (Low weight: 0.5 per hit)
        content_lower = doc.raw_content.lower()
        for cat, keywords in self.keyword_rules.items():
            for kw in keywords:
                count = content_lower.count(kw)
                if count > 0:
                    scores[cat] += min(count * 0.5, 3.0)

        # Select highest scoring category
        best_category = "Misc"
        best_score = 0.0

        for cat, score in scores.items():
            if cat != "Misc" and score > best_score:
                best_score = score
                best_category = cat

        # Require a minimum confidence threshold of 2.0 to assign specific category
        if best_score < 2.0:
            best_category = "Misc"

        logger.debug(
            f"Classified '{doc.filename}' as '{best_category}' (Score: {best_score:.1f})"
        )
        return best_category
