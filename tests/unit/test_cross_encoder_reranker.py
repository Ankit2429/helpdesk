"""Unit tests for CrossEncoderReranker and RAGPipeline integration."""

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.cross_encoder_reranker import CrossEncoderReranker


def test_cross_encoder_reranker_disabled():
    reranker = CrossEncoderReranker(enabled=False)
    doc1 = KnowledgeDocument(content="Library hours: 8am to 8pm", metadata={"source": "lib.md"})
    doc2 = KnowledgeDocument(content="Admissions contact details", metadata={"source": "adm.md"})
    matches = [SearchResult(document=doc1, distance=0.1), SearchResult(document=doc2, distance=0.2)]

    results, stats = reranker.rerank_with_stats("What are the library hours?", matches)

    assert stats["reranker_status"] == "disabled"
    assert len(results) == 2
    assert results[0].document.metadata["source"] == "lib.md"


def test_cross_encoder_reranker_metadata_preservation():
    # Test with disabled flag to verify fallback pass-through preserves all metadata fields
    reranker = CrossEncoderReranker(enabled=False)
    doc = KnowledgeDocument(
        content="Campus Central Library FAQ",
        metadata={"source": "library.md", "title": "Library FAQ", "section": "Hours", "category": "General"},
    )
    match = SearchResult(document=doc, distance=0.15)

    results = reranker.rerank("library hours", [match])
    assert len(results) == 1
    assert results[0].document.metadata["title"] == "Library FAQ"
    assert results[0].document.metadata["section"] == "Hours"
    assert results[0].document.metadata["category"] == "General"


def test_cross_encoder_reranker_fallback_on_invalid_model():
    reranker = CrossEncoderReranker(model_name="nonexistent/fake-model-xyz", enabled=True)
    doc = KnowledgeDocument(content="Sample text", metadata={"source": "sample.md"})
    match = SearchResult(document=doc, distance=0.1)

    results, stats = reranker.rerank_with_stats("sample query", [match])

    assert stats["reranker_status"] in ("fallback", "error_fallback")
    assert len(results) == 1
    assert results[0].document.content == "Sample text"
