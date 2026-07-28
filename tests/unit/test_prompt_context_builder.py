"""Unit tests for PromptContextBuilder and retrieval integration."""

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder


def test_prompt_context_builder_formatting_and_citations():
    builder = PromptContextBuilder(max_context_size=1000, similarity_threshold=2.0)
    doc1 = KnowledgeDocument(
        content="The Central Library is in Block C, 2nd floor.",
        metadata={
            "source": "library.md",
            "title": "Central Library Guide",
            "Header 2": "Location",
        },
    )
    results = [SearchResult(document=doc1, distance=0.35)]

    context = builder.build_context(results)

    assert "[Source: library.md | Title: Central Library Guide | Section: Location]" in context
    assert "The Central Library is in Block C, 2nd floor." in context


def test_prompt_context_builder_threshold_filtering():
    builder = PromptContextBuilder(max_context_size=1000, similarity_threshold=1.5)
    good_doc = KnowledgeDocument(content="Good match content", metadata={"source": "good.md"})
    bad_doc = KnowledgeDocument(content="Irrelevant match content", metadata={"source": "bad.md"})

    results = [
        SearchResult(document=good_doc, distance=0.8),
        SearchResult(document=bad_doc, distance=2.5),  # Exceeds 1.5 threshold
    ]

    context = builder.build_context(results)

    assert "good.md" in context
    assert "bad.md" not in context


def test_prompt_context_builder_deduplication():
    builder = PromptContextBuilder(max_context_size=1000, similarity_threshold=2.0)
    doc = KnowledgeDocument(content="Identical chunk text", metadata={"source": "doc1.md"})

    results = [
        SearchResult(document=doc, distance=0.4),
        SearchResult(document=doc, distance=0.45),  # Duplicate
    ]

    context = builder.build_context(results)

    assert context.count("Identical chunk text") == 1


def test_prompt_context_builder_max_context_size():
    builder = PromptContextBuilder(max_context_size=100, similarity_threshold=2.0)
    doc1 = KnowledgeDocument(content="Chunk 1 short content", metadata={"source": "doc1.md"})
    doc2 = KnowledgeDocument(
        content="Chunk 2 very long content that will exceed the maximum context size cap",
        metadata={"source": "doc2.md"},
    )

    results = [
        SearchResult(document=doc1, distance=0.1),
        SearchResult(document=doc2, distance=0.2),
    ]

    context = builder.build_context(results)
    assert len(context) <= 100
