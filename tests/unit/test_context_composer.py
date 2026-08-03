"""Unit tests for ContextComposer chunk deduplication, -dup collapsing, and citation preservation."""

import pytest
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer


def create_search_result(content: str, source_filename: str, distance: float = 0.5) -> SearchResult:
    doc = KnowledgeDocument(
        content=content,
        metadata={
            "source": source_filename,
            "source_filename": source_filename,
            "parent_document": source_filename,
            "breadcrumb": f"Campus > {source_filename}",
        },
    )
    return SearchResult(document=doc, distance=distance)


def test_collapse_dup_filename_pair():
    """Verify ContextComposer collapses -dup files when canonical version is present."""
    res_fee = create_search_result(
        "General university fee payment options and installment details.",
        "fee-structure.md",
    )
    res_course = create_search_result(
        "BE course fee structure: KCET quota is Rs 1,12,410 per annum.",
        "course-fee-structure.md",
    )
    res_course_dup = create_search_result(
        "BE course fee structure: KCET quota is Rs 1,12,410 per annum.",
        "course-fee-structure-dup.md",
    )

    composer = ContextComposer(enable_composer=True)
    composed = composer.compose([res_fee, res_course, res_course_dup])

    # course-fee-structure-dup.md must be collapsed
    sources = [r.document.metadata["source"] for r in composed]
    assert "course-fee-structure-dup.md" not in sources
    assert "course-fee-structure.md" in sources
    assert "fee-structure.md" in sources
    assert len(composed) == 2


def test_distinct_sources_not_merged():
    """Verify two genuinely different sources with similar introductory wording are NOT merged."""
    text1 = (
        "KLE Technological University, Hubballi. School of Computer Science & Engineering. "
        "Tuition fee for CSE under COMEDK quota is Rs 4,00,000 per annum."
    )
    text2 = (
        "KLE Technological University, Hubballi. School of Computer Science & Engineering. "
        "Hostel facilities for boys and girls include mess, Wi-Fi, and 24/7 security."
    )

    res1 = create_search_result(text1, "cse-fees.md")
    res2 = create_search_result(text2, "hostel-rules.md")

    composer = ContextComposer(enable_composer=True, dedup_threshold=0.85)
    composed = composer.compose([res1, res2])

    # Both distinct sources must survive
    assert len(composed) == 2
    assert composed[0].document.metadata["source"] == "cse-fees.md"
    assert composed[1].document.metadata["source"] == "hostel-rules.md"


def test_content_similarity_deduplication():
    """Verify near-identical chunk text across differently named files is deduplicated."""
    text_canonical = "The Vice Chancellor of KLE Technological University is Dr. Prakash G. Tewari."
    text_duplicate = "The Vice Chancellor of KLE Technological University is Dr. Prakash G. Tewari."

    res1 = create_search_result(text_canonical, "vc-profile.md")
    res2 = create_search_result(text_duplicate, "leadership-news.md")

    composer = ContextComposer(enable_composer=True, dedup_threshold=0.85)
    composed = composer.compose([res1, res2])

    assert len(composed) == 1
    assert composed[0].document.metadata["source"] == "vc-profile.md"


def test_composer_disabled_passthrough():
    """Verify composer behaves as passthrough when enable_composer=False."""
    res1 = create_search_result("Test content", "file.md")
    res2 = create_search_result("Test content", "file-dup.md")

    composer = ContextComposer(enable_composer=False)
    composed = composer.compose([res1, res2])

    assert len(composed) == 2


def test_context_budget_limit():
    """Verify composer enforces max_context_size budget limit."""
    res1 = create_search_result("A" * 4000, "doc1.md")
    res2 = create_search_result("B" * 4000, "doc2.md")

    composer = ContextComposer(enable_composer=True, max_context_size=5000)
    composed = composer.compose([res1, res2])

    assert len(composed) == 1
    assert composed[0].document.metadata["source"] == "doc1.md"


def test_citation_metadata_preserved():
    """Verify all document metadata and SearchResult fields are preserved untouched."""
    res = create_search_result("Sample content for verification", "sample.md", distance=0.25)
    composer = ContextComposer(enable_composer=True)
    composed = composer.compose([res])

    assert len(composed) == 1
    assert composed[0].distance == 0.25
    assert composed[0].document.metadata["source"] == "sample.md"
    assert composed[0].document.metadata["breadcrumb"] == "Campus > sample.md"
