"""Unit tests for Markdown-aware semantic chunker and structural statistics."""

from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.markdown_chunker import MarkdownSemanticChunker
from campus_helpdesk.infrastructure.rag.semantic_chunker import (
    SemanticDocumentChunker,
    compute_chunk_statistics,
)


def test_markdown_semantic_chunker_header_splitting():
    content = (
        "# Campus Overview\n\n"
        "The campus was established in 1964.\n\n"
        "## Central Library\n\n"
        "Located in Block C, 2nd floor.\n\n"
        "### Operating Hours\n\n"
        "Mon-Sat: 8 AM - 8 PM."
    )
    doc = KnowledgeDocument(content=content, metadata={"source": "overview.md", "title": "Overview"})
    chunker = MarkdownSemanticChunker(chunk_size=500, chunk_overlap=50)

    chunks = chunker.split_document(doc)

    assert len(chunks) >= 1
    assert "section_title" in chunks[0].metadata or "page_title" in chunks[0].metadata

    # Metadata propagation check
    for c in chunks:
        assert c.metadata["source"] == "overview.md"
        assert c.metadata["title"] == "Overview"


def test_markdown_semantic_chunker_table_preservation():
    table_markdown = (
        "# Fee Structure\n\n"
        "| Department | Tuition Fee | Hostel Fee |\n"
        "| --- | --- | --- |\n"
        "| Computer Science | 75,000 | 25,000 |\n"
        "| Mechanical | 70,000 | 25,000 |\n\n"
        "## Payment Options\n\n"
        "Pay via online portal."
    )
    doc = KnowledgeDocument(content=table_markdown, metadata={"source": "fees.md"})
    chunker = MarkdownSemanticChunker(chunk_size=500, chunk_overlap=50)

    chunks = chunker.split_document(doc)

    assert len(chunks) >= 1
    # Ensure the table header and rows stay intact in chunk 0
    assert "| Department | Tuition Fee | Hostel Fee |" in chunks[0].content
    assert "| Mechanical | 70,000 | 25,000 |" in chunks[0].content


def test_semantic_document_chunker_routing():
    md_doc = KnowledgeDocument(
        content="# Section A\n\nSection A details.",
        metadata={"source": "guide.md"},
    )
    pdf_doc = KnowledgeDocument(
        content="PDF page 1 text content without markdown headers.",
        metadata={"source": "brochure.pdf"},
    )

    chunker = SemanticDocumentChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.split([md_doc, pdf_doc])

    assert len(chunks) >= 1
    assert chunks[-1].metadata["source"] == "brochure.pdf"


def test_compute_chunk_statistics():
    chunks = [
        KnowledgeDocument(content="Short chunk", metadata={}),
        KnowledgeDocument(content="A much longer knowledge document chunk content", metadata={}),
    ]

    stats = compute_chunk_statistics(chunks)

    assert stats["number_of_chunks"] == 2
    assert stats["smallest_chunk_size"] == len("Short chunk")
    assert stats["largest_chunk_size"] == len("A much longer knowledge document chunk content")
    assert stats["average_chunk_size"] > 0
