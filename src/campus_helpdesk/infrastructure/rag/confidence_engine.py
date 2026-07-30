import logging
import math
import time
from dataclasses import dataclass, field
from typing import Sequence, List, Dict

from campus_helpdesk.config.settings import Settings, get_settings
from campus_helpdesk.domain.knowledge import SearchResult

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """Confidence evaluation result containing normalized score, level, and evidence breakdown."""

    confidence_score: float
    confidence_level: str  # "Very High", "High", "Medium", "Low", "Very Low"
    supporting_chunk_count: int
    top_reranker_score: float
    top_distance: float
    supporting_sources: List[str] = field(default_factory=list)
    diagnostics: Dict[str, float] = field(default_factory=dict)
    evidence_consistency: float = 0.0
    citation_quality: float = 0.0
    hallucination_risk: str = "UNKNOWN"
    reason: str = ""

class ConfidenceEngine:
    """Deterministic confidence calculator using configurable weights and signals."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        # Configurable weights and thresholds
        self.weights: Dict[str, float] = self.settings.confidence_weights
        self.thresholds: Dict[str, float] = self.settings.confidence_thresholds
        self.risk_thresholds: Dict[str, float] = self.settings.hallucination_risk_thresholds

    def _evidence_consistency(self, search_results: Sequence[SearchResult]) -> float:
        """Simple token‑overlap consistency between retrieved chunks (0‑1)."""
        token_sets: List[set] = []
        for res in search_results:
            text = getattr(res.document, "content", "") or getattr(res.document, "text", "")
            tokens = set(text.lower().split())
            token_sets.append(tokens)
        if not token_sets:
            return 0.0
        intersect = set.intersection(*token_sets)
        union = set.union(*token_sets)
        return len(intersect) / max(1, len(union))

    def _citation_quality(self, search_results: Sequence[SearchResult]) -> float:
        """Proportion of chunks that contain a citation marker (naïve)."""
        if not search_results:
            return 0.0
        cited = 0
        for res in search_results:
            txt = getattr(res.document, "content", "") or getattr(res.document, "text", "")
            if "[C" in txt:
                cited += 1
        return cited / len(search_results)

    def evaluate(self, search_results: Sequence[SearchResult]) -> ConfidenceAssessment:
        """Compute all signals, apply weights, and return a populated ConfidenceAssessment."""
        if not search_results:
            return ConfidenceAssessment(
                confidence_score=0.0,
                confidence_level="Very Low",
                supporting_chunk_count=0,
                top_reranker_score=-99.0,
                top_distance=99.0,
                supporting_sources=[],
                diagnostics={},
                evidence_consistency=0.0,
                citation_quality=0.0,
                hallucination_risk="Very High",
                reason="No results",
            )

        start_time = time.time()
        top_match = search_results[0]
        top_reranker_score = -top_match.distance if top_match.distance < 0 else 0.0
        top_distance = top_match.distance if top_match.distance >= 0 else 0.5

        # Reranker signal (sigmoid on cross‑encoder score)
        if top_match.distance < 0:
            reranker_signal = 1.0 / (1.0 + math.exp(-top_reranker_score / 2.5))
        else:
            reranker_signal = max(0.0, min(1.0, 1.0 - (top_distance / 2.0)))

        # Distance signal (inverse of FAISS distance)
        distance_signal = max(0.0, min(1.0, 1.0 - (top_distance / 2.0)))

        # Chunk count signal (normalized to 4 chunks)
        num_chunks = len(search_results)
        count_signal = min(1.0, num_chunks / 4.0)

        # Source diversity signal
        sources = [m.document.metadata.get("source", "unknown") for m in search_results]
        unique_sources = list(dict.fromkeys(sources))
        source_diversity_signal = len(unique_sources) / max(1, num_chunks)

        # Evidence consistency & citation quality signals
        evidence_consistency_signal = self._evidence_consistency(search_results)
        citation_quality_signal = self._citation_quality(search_results)

        # Composite weighted score
        signals = {
            "reranker": reranker_signal,
            "distance": distance_signal,
            "count": count_signal,
            "source_diversity": source_diversity_signal,
            "evidence_consistency": evidence_consistency_signal,
            "citation_quality": citation_quality_signal,
        }
        composite_score = 0.0
        for name, weight in self.weights.items():
            composite_score += weight * signals.get(name, 0.0)
        confidence_score = round(max(0.0, min(1.0, composite_score)), 4)

        # Determine confidence level (5 tiers)
        high_thr = self.thresholds.get("high", 0.80)
        med_thr = self.thresholds.get("medium", 0.55)
        low_thr = self.thresholds.get("low", 0.30)
        if confidence_score >= high_thr:
            confidence_level = "Very High"
        elif confidence_score >= med_thr:
            confidence_level = "High"
        elif confidence_score >= low_thr:
            confidence_level = "Medium"
        elif confidence_score >= (low_thr * 0.5):
            confidence_level = "Low"
        else:
            confidence_level = "Very Low"

        # Hallucination risk – derived from evidence consistency (higher risk = lower consistency)
        risk_score = 1.0 - evidence_consistency_signal
        if risk_score <= self.risk_thresholds.get("very_low", 0.2):
            hallucination_risk = "Very Low"
        elif risk_score <= self.risk_thresholds.get("low", 0.4):
            hallucination_risk = "Low"
        elif risk_score <= self.risk_thresholds.get("medium", 0.6):
            hallucination_risk = "Medium"
        elif risk_score <= self.risk_thresholds.get("high", 0.8):
            hallucination_risk = "High"
        else:
            hallucination_risk = "Very High"

        diagnostics = {
            "reranker_signal": round(reranker_signal, 4),
            "distance_signal": round(distance_signal, 4),
            "count_signal": round(count_signal, 4),
            "source_diversity_signal": round(source_diversity_signal, 4),
            "evidence_consistency_signal": round(evidence_consistency_signal, 4),
            "citation_quality_signal": round(citation_quality_signal, 4),
        }

        elapsed = time.time() - start_time
        logger.debug(
            "ConfidenceEngine evaluated in %.4fs – score=%.4f, level=%s, risk=%s",
            elapsed,
            confidence_score,
            confidence_level,
            hallucination_risk,
        )

        return ConfidenceAssessment(
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            supporting_chunk_count=num_chunks,
            top_reranker_score=round(top_reranker_score, 4),
            top_distance=round(top_distance, 4),
            supporting_sources=unique_sources,
            diagnostics=diagnostics,
            evidence_consistency=round(evidence_consistency_signal, 4),
            citation_quality=round(citation_quality_signal, 4),
            hallucination_risk=hallucination_risk,
            reason="",
        )
