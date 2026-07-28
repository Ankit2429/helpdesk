"""Confidence & Evidence Engine for assessing retrieved context strength and hallucination risk."""

import logging
import math
from dataclasses import dataclass, field
from typing import Sequence

from campus_helpdesk.domain.knowledge import SearchResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """Confidence evaluation result containing normalized score, level, and evidence breakdown."""

    confidence_score: float
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    supporting_chunk_count: int
    top_reranker_score: float
    top_distance: float
    supporting_sources: list[str] = field(default_factory=list)
    diagnostics: dict[str, float] = field(default_factory=dict)


class ConfidenceEngine:
    """Evaluates multi-signal evidence metrics to assign normalized confidence scores to retrieval context."""

    def __init__(
        self,
        high_threshold: float = 0.70,
        medium_threshold: float = 0.45,
    ) -> None:
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def evaluate(self, search_results: Sequence[SearchResult]) -> ConfidenceAssessment:
        """Evaluate multi-signal evidence metrics from candidate search results."""
        if not search_results:
            return ConfidenceAssessment(
                confidence_score=0.0,
                confidence_level="LOW",
                supporting_chunk_count=0,
                top_reranker_score=-99.0,
                top_distance=99.0,
                supporting_sources=[],
                diagnostics={"reranker_signal": 0.0, "distance_signal": 0.0, "count_signal": 0.0},
            )

        top_match = search_results[0]
        # In CrossEncoderReranker, distance = -cross_encoder_score
        top_reranker_score = -top_match.distance if top_match.distance < 0 else 0.0
        top_distance = top_match.distance if top_match.distance >= 0 else 0.5

        # 1. Reranker Signal (Normalized sigmoid transform of cross-encoder score)
        # MS-MARCO CrossEncoder scores typically range from -10 to +8
        if top_match.distance < 0:  # Reranker was active
            reranker_signal = 1.0 / (1.0 + math.exp(-top_reranker_score / 2.5))
        else:
            # Distance signal (distance ranges 0.0 to 2.0)
            reranker_signal = max(0.0, min(1.0, 1.0 - (top_distance / 2.0)))

        # 2. Distance Signal
        distance_signal = max(0.0, min(1.0, 1.0 - (top_distance / 2.0)))

        # 3. Supporting Chunks Count Signal
        num_chunks = len(search_results)
        count_signal = min(1.0, num_chunks / 4.0)

        # 4. Source Diversity / Agreement Signal
        sources = [match.document.metadata.get("source", "unknown") for match in search_results]
        unique_sources = list(dict.fromkeys(sources))

        # Composite weighted score formula
        composite_score = (0.55 * reranker_signal) + (0.30 * distance_signal) + (0.15 * count_signal)
        confidence_score = round(max(0.0, min(1.0, composite_score)), 4)

        if confidence_score >= self.high_threshold:
            confidence_level = "HIGH"
        elif confidence_score >= self.medium_threshold:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        diagnostics = {
            "reranker_signal": round(reranker_signal, 4),
            "distance_signal": round(distance_signal, 4),
            "count_signal": round(count_signal, 4),
        }

        logger.info(
            "Confidence Assessment: Score=%.4f, Level=%s, Chunks=%d, TopScore=%.2f",
            confidence_score,
            confidence_level,
            num_chunks,
            top_reranker_score,
        )

        return ConfidenceAssessment(
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            supporting_chunk_count=num_chunks,
            top_reranker_score=round(top_reranker_score, 4),
            top_distance=round(top_distance, 4),
            supporting_sources=unique_sources,
            diagnostics=diagnostics,
        )
