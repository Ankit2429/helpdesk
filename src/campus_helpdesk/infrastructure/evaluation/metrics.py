"""Calculates evaluation metrics for RAG retrieval and answer generation."""

from collections.abc import Sequence


def calculate_recall_at_k(retrieved_sources: Sequence[str], expected_sources: Sequence[str], k: int) -> float:
    """Calculate Recall@K ratio of expected sources present in top K retrieved chunks."""
    if not expected_sources:
        return 1.0

    top_k_sources = [s.lower() for s in retrieved_sources[:k]]
    matches = sum(1 for exp in expected_sources if any(exp.lower() in src for src in top_k_sources))
    return matches / len(expected_sources)


def calculate_mrr(retrieved_sources: Sequence[str], expected_sources: Sequence[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR) for the first matching expected source."""
    if not expected_sources:
        return 1.0

    expected_lower = [exp.lower() for exp in expected_sources]
    for rank, src in enumerate(retrieved_sources, start=1):
        src_lower = src.lower()
        if any(exp in src_lower for exp in expected_lower):
            return 1.0 / rank

    return 0.0


def calculate_keyword_coverage(text: str, expected_keywords: Sequence[str]) -> tuple[float, list[str], list[str]]:
    """Calculate keyword coverage ratio, matched keywords, and missing keywords."""
    if not expected_keywords:
        return 1.0, [], []

    lower_text = text.lower()
    matched = []
    missing = []

    for kw in expected_keywords:
        kw_str = str(kw)
        if kw_str.lower() in lower_text:
            matched.append(kw_str)
        else:
            missing.append(kw_str)

    ratio = len(matched) / len(expected_keywords)
    return ratio, matched, missing
