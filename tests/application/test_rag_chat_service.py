"""Unit tests for RAGChatService hallucination guarding and distance threshold checks."""

from campus_helpdesk.application.rag_chat_service import FALLBACK_NO_INFO_REPLY, RAGChatService
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult


class DummyLLMService:
    """Records whether generate was called."""

    def __init__(self) -> None:
        self.called = False

    def generate(self, prompt: str) -> str:
        self.called = True
        return "LLM Generated Response"


class FakeHighDistancePipeline:
    """Returns a search result with a high FAISS distance score (low similarity)."""

    def search(self, query: str) -> list[SearchResult]:
        doc = KnowledgeDocument(content="Irrelevant document content", metadata={})
        # Distance 2.5 > threshold 1.0
        return [SearchResult(document=doc, distance=2.5)]


def test_rag_chat_service_returns_fallback_on_high_distance_without_calling_llm() -> None:
    llm = DummyLLMService()
    pipeline = FakeHighDistancePipeline()
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline, distance_threshold=1.0)

    result = service.respond("What is the wifi password?")

    assert not llm.called
    assert result.reply == FALLBACK_NO_INFO_REPLY
    assert result.status == "completed"
