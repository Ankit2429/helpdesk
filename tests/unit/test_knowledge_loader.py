"""Unit tests for generic KnowledgeLoader and format adapters."""

import tempfile
from pathlib import Path

import pytest
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader


def test_markdown_knowledge_loader_valid():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root_dir = Path(tmp_dir)
        md_file = root_dir / "library_hours.md"
        content = (
            "---\n"
            "title: Library Hours Guide\n"
            "category: Services\n"
            "---\n"
            "# Central Library Hours\n\n"
            "The library is open from 8:00 AM to 8:00 PM."
        )
        md_file.write_text(content, encoding="utf-8")

        loader = MarkdownKnowledgeLoader(knowledge_source_path=root_dir, max_file_size_bytes=1024 * 1024)
        docs = loader.load(md_file)

        assert len(docs) == 1
        doc = docs[0]
        assert isinstance(doc, KnowledgeDocument)
        assert doc.metadata["title"] == "Library Hours Guide"
        assert doc.metadata["category"] == "Services"
        assert "source" in doc.metadata
        assert "The library is open from 8:00 AM to 8:00 PM." in doc.content
        assert "---" not in doc.content  # Frontmatter header stripped from indexed content


def test_markdown_knowledge_loader_invalid_extension():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root_dir = Path(tmp_dir)
        txt_file = root_dir / "info.txt"
        txt_file.write_text("Plain text content", encoding="utf-8")

        loader = MarkdownKnowledgeLoader(knowledge_source_path=root_dir, max_file_size_bytes=1024 * 1024)
        with pytest.raises(ValueError, match="Only Markdown files"):
            loader.load(txt_file)


def test_knowledge_loader_composite():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root_dir = Path(tmp_dir)
        md_file = root_dir / "guide.md"
        md_file.write_text("# Guide Title\n\nCampus details here.", encoding="utf-8")

        invalid_file = root_dir / "document.docx"
        invalid_file.write_text("Docx content", encoding="utf-8")

        loader = KnowledgeLoader(knowledge_source_path=root_dir, max_file_size_bytes=1024 * 1024)

        # Test .md dispatch
        md_docs = loader.load(md_file)
        assert len(md_docs) == 1
        assert "Campus details here." in md_docs[0].content

        # Test unsupported extension dispatch
        with pytest.raises(ValueError, match="Unsupported knowledge source extension"):
            loader.load(invalid_file)


def test_rag_pipeline_backward_compatibility():
    from campus_helpdesk.application.rag_pipeline import RAGPipeline

    class MockLoader:
        def load(self, source_path: Path) -> list[KnowledgeDocument]:
            return [KnowledgeDocument(content="Test content", metadata={"source": str(source_path)})]

    class MockChunker:
        def split(self, documents):
            return documents

    class MockStore:
        def __init__(self):
            self.added = []

        def add(self, documents):
            self.added.extend(documents)

        def save(self):
            pass

    mock_loader = MockLoader()
    mock_chunker = MockChunker()
    mock_store = MockStore()

    pipeline = RAGPipeline(
        document_loader=mock_loader,
        document_chunker=mock_chunker,
        similarity_store=mock_store,
        search_limit=5,
    )

    # Ingest file via ingest_pdf backward-compatible alias
    res = pipeline.ingest_pdf(Path("sample.pdf"), persist=False)
    assert res.document_count == 1
    assert res.chunk_count == 1
    assert len(mock_store.added) == 1
