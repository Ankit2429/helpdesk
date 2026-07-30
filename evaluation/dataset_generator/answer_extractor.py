"""Answer Extractor Module.

Ensures every expected answer is strictly extracted verbatim or via grounded factual selection
from the current Markdown section ONLY. Prevents information invention and cross-file pollution.
"""

import logging
import re
from typing import Optional

from evaluation.dataset_generator.reader import SectionBlock

logger = logging.getLogger(__name__)


class AnswerExtractor:
    """Extracts grounded answer excerpts from Markdown section blocks."""

    def extract_answer(
        self, section: SectionBlock, max_words: int = 100
    ) -> Optional[str]:
        """Extracts a factual answer excerpt strictly from section content.

        Args:
            section: Source SectionBlock.
            max_words: Upper word count limit for the answer snippet.

        Returns:
            Cleaned answer string grounded in section content, or None if invalid.
        """
        content = section.content.strip()
        if not content:
            return None

        # Clean markdown formatting (links, bold, italics, tables syntax)
        clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)  # Markdown links
        clean_text = re.sub(r"[*_~`#]", "", clean_text)                # Style markers
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        words = clean_text.split()
        if len(words) < 3:
            return None

        # Trim to max_words at sentence boundary
        if len(words) > max_words:
            truncated = " ".join(words[:max_words])
            last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
            if last_period > 20:
                answer = truncated[: last_period + 1]
            else:
                answer = truncated + "..."
        else:
            answer = clean_text

        # Verify that answer contains content from the original section (no hallucination)
        if answer.lower() not in content.lower() and not any(w.lower() in content.lower() for w in words[:4]):
            logger.warning(f"Answer extraction grounding check failed for section '{section.heading}'")
            return None

        return answer
