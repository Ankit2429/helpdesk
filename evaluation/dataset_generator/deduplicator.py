"""Semantic Deduplicator Module.

Identifies and purges exact duplicates, near-duplicates, and redundant phrasing variants
from synthesized dataset candidates.
"""

import difflib
import logging
import re
from typing import List, Set, Tuple

from evaluation.dataset_generator.question_generator import GeneratedQuestionCandidate

logger = logging.getLogger(__name__)


def _normalize_query(text: str) -> str:
    """Normalizes query string for similarity comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


class SemanticDeduplicator:
    """Removes duplicate and near-duplicate benchmark queries."""

    def __init__(self, threshold: float = 0.85):
        """Initializes deduplicator with similarity threshold (default 0.85)."""
        self.threshold = threshold

    def deduplicate(
        self, candidates: List[GeneratedQuestionCandidate]
    ) -> Tuple[List[GeneratedQuestionCandidate], int]:
        """Deduplicates a list of candidate question objects.

        Args:
            candidates: List of GeneratedQuestionCandidate instances.

        Returns:
            Tuple of (deduplicated_candidates, count_removed).
        """
        unique_candidates: List[GeneratedQuestionCandidate] = []
        seen_normalized: List[str] = []
        seen_token_sets: List[Set[str]] = []
        removed_count = 0

        for cand in candidates:
            norm = _normalize_query(cand.question)
            if not norm:
                removed_count += 1
                continue

            tokens = set(norm.split())
            is_dup = False

            for idx, existing_norm in enumerate(seen_normalized):
                # 1. Exact normalized match
                if norm == existing_norm:
                    is_dup = True
                    break

                # 2. Length difference check (Fast exit)
                len_diff = abs(len(norm) - len(existing_norm))
                max_len = max(len(norm), len(existing_norm))
                if max_len > 0 and (len_diff / float(max_len)) > (1.0 - self.threshold):
                    continue

                # 3. Jaccard word set similarity
                existing_tokens = seen_token_sets[idx]
                if tokens and existing_tokens:
                    intersection = len(tokens & existing_tokens)
                    union = len(tokens | existing_tokens)
                    if union > 0 and (intersection / float(union)) >= self.threshold:
                        is_dup = True
                        break

                # 4. SequenceMatcher fuzzy ratio
                seq_ratio = difflib.SequenceMatcher(None, norm, existing_norm).ratio()
                if seq_ratio >= self.threshold:
                    is_dup = True
                    break

            if is_dup:
                removed_count += 1
                logger.debug(f"[Deduplication] Dropping duplicate query: '{cand.question}'")
            else:
                unique_candidates.append(cand)
                seen_normalized.append(norm)
                seen_token_sets.append(tokens)

        return unique_candidates, removed_count
