"""Unit tests for ConfidenceEngine evidence evaluation and scoring."""

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine


def test_confidence_engine_high_confidence():
    engine = ConfidenceEngine(high_threshold=0.70, medium_threshold=0.45)

    # In CrossEncoderReranker, distance = -cross_encoder_score. Distance -5.0 = CrossEncoder score +5.0
    doc1 = KnowledgeDocument(content="Library location info", metadata={"source": "lib.md"})
    doc2 = KnowledgeDocument(content="Library hours info", metadata={"source": "lib.md"})
    doc3 = KnowledgeDocument(content="Library FAQ info", metadata={"source": "lib_faq.md"})

    matches = [
        SearchResult(document=doc1, distance=-5.0),
        SearchResult(document=doc2, distance=-4.5),
        SearchResult(document=doc3, distance=-3.0),
    ]

    assessment = engine.evaluate(matches)

    assert assessment.confidence_level == "HIGH"
    assert assessment.confidence_score >= 0.70
    assert assessment.supporting_chunk_count == 3
    assert "lib.md" in assessment.supporting_sources


def test_confidence_engine_low_confidence():
    engine = ConfidenceEngine(high_threshold=0.70, medium_threshold=0.45)

    # Low relevance: negative cross-encoder score -8.0 -> distance = +8.0
    doc = KnowledgeDocument(content="Unrelated campus note", metadata={"source": "note.md"})
    matches = [SearchResult(document=doc, distance=8.0)]

    assessment = engine.evaluate(matches)

    assert assessment.confidence_level == "LOW"
    assert assessment.confidence_score < 0.45


def test_confidence_engine_empty_results():
    engine = ConfidenceEngine()

    assessment = engine.evaluate([])

    assert assessment.confidence_score == 0.0
    assert assessment.confidence_level == "LOW"
    assert assessment.supporting_chunk_count == 0
    assert len(assessment.supporting_sources) == 0
