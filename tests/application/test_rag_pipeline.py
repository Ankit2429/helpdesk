"""Tests for RAG pipeline orchestration."""

from pathlib import Path

from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult


class FakeDocumentLoader:
    """Returns a fixed source document for pipeline testing."""

    def load(self, source_path: Path) -> list[KnowledgeDocument]:
        return [KnowledgeDocument(content="Campus library hours", metadata={"source": str(source_path)})]


class FakeDocumentChunker:
    """Returns one retrieval chunk."""

    def split(self, documents: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
        return [KnowledgeDocument(content="Library opens at 8 AM", metadata=documents[0].metadata)]


class FakeSimilarityStore:
    """Records indexing interactions and returns a fixed search result."""

    def __init__(self) -> None:
        self.added_documents: list[KnowledgeDocument] = []
        self.did_save = False
        self.did_load = False

    def add(self, documents: list[KnowledgeDocument]) -> None:
        self.added_documents.extend(documents)

    def search(self, query: str, limit: int) -> list[SearchResult]:
        return [SearchResult(document=self.added_documents[0], distance=0.25)]

    def save(self) -> None:
        self.did_save = True

    def load(self) -> None:
        self.did_load = True


def test_pipeline_ingests_and_searches_pdf_content() -> None:
    store = FakeSimilarityStore()
    pipeline = RAGPipeline(FakeDocumentLoader(), FakeDocumentChunker(), store, search_limit=3)

    result = pipeline.ingest_pdf(Path("knowledge.pdf"))
    matches = pipeline.search("When does the library open?")

    assert result.document_count == 1
    assert result.chunk_count == 1
    assert store.did_save is True
    assert matches[0].document.content == "Library opens at 8 AM"
