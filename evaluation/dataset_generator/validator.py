"""Quality Validator Module for Dataset Generator.

Filters out ambiguous questions, empty answers, hallucinated responses,
and examples unsupported by the source Markdown file.
"""

import logging
import re
from typing import Tuple

from evaluation.dataset_generator.config import GeneratorConfig
from evaluation.dataset_generator.question_generator import GeneratedQuestionCandidate
from evaluation.dataset_generator.reader import MarkdownDocument

logger = logging.getLogger(__name__)


class DatasetValidator:
    """Validates candidate benchmark dataset entries."""

    def __init__(self, config: GeneratorConfig):
        self.config = config

    def validate_candidate(
        self, candidate: GeneratedQuestionCandidate, doc: MarkdownDocument
    ) -> Tuple[bool, str]:
        """Validates a generated candidate question-answer pair against the source document.

        Args:
            candidate: GeneratedQuestionCandidate instance.
            doc: Source MarkdownDocument.

        Returns:
            Tuple of (is_valid: bool, rejection_reason: str).
        """
        question = candidate.question.strip()
        answer = candidate.expected_answer.strip()

        # 1. Question presence & length validation
        if not question:
            return False, "Empty question text"
        if len(question) < 8:
            return False, f"Question too short ({len(question)} chars)"

        # 2. Answer presence & length validation
        if not answer:
            return False, "Empty answer text"
        answer_words = len(answer.split())
        if answer_words < self.config.min_answer_length:
            return False, f"Answer length below minimum ({answer_words} words)"
        if answer_words > self.config.max_answer_length:
            return False, f"Answer length exceeds maximum ({answer_words} words)"

        # 3. Groundedness validation (verify answer terms exist inside source markdown)
        raw_doc_lower = doc.raw_content.lower()
        ans_keywords = [w.lower() for w in re.sub(r"[^\w\s]", "", answer).split() if len(w) > 3]

        if ans_keywords:
            grounded_count = sum(1 for kw in ans_keywords if kw in raw_doc_lower)
            grounded_ratio = grounded_count / float(len(ans_keywords))
            if grounded_ratio < 0.6:
                return False, f"Ungrounded answer (only {grounded_ratio*100:.1f}% keywords found in document)"

        # 4. Ambiguity / generic question check
        generic_patterns = [r"^what is this\??$", r"^details\??$", r"^information\??$"]
        for pat in generic_patterns:
            if re.match(pat, question.lower()):
                return False, f"Ambiguous generic question pattern: '{question}'"

        return True, "Valid"
