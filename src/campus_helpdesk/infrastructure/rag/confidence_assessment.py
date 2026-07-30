from dataclasses import dataclass, field
from typing import Any, List

# Extended ConfidenceAssessment used by ConfidenceEngine and AnswerVerificationEngine
@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """Confidence evaluation result containing normalized score, level, and evidence breakdown."""

    confidence_score: float
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    supporting_chunk_count: int
    top_reranker_score: float
    top_distance: float
    supporting_sources: List[str] = field(default_factory=list)
    diagnostics: dict[str, float] = field(default_factory=dict)
    # New fields for richer evaluation
    evidence_consistency: float = 0.0
    citation_quality: float = 0.0
    hallucination_risk: str = "UNKNOWN"
    reason: str = ""
