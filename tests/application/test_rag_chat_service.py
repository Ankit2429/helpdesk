"""Unit tests for RAGChatService hallucination guarding and distance threshold checks."""

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult


class DummyLLMService:
    """Records whether generate was called and captures the prompt."""

    def __init__(self) -> None:
        self.called = False
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.called = True
        self.last_prompt = prompt
        return "LLM Generated Response"


class FakeHighDistancePipeline:
    """Returns a search result with a high FAISS distance score (low similarity)."""

    def search(self, query: str) -> list[SearchResult]:
        doc = KnowledgeDocument(content="Irrelevant document content", metadata={})
        # Distance 2.5 > threshold 1.0
        return [SearchResult(document=doc, distance=2.5)]


def test_rag_chat_service_falls_back_to_llm_on_high_distance() -> None:
    """When RAG results exceed the distance threshold, the LLM should still be called
    with a general knowledge prompt rather than returning a dead-end fallback."""
    llm = DummyLLMService()
    pipeline = FakeHighDistancePipeline()
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline, distance_threshold=1.0)

    result = service.respond("What is the wifi password?")

    assert llm.called
    assert "Context:" not in llm.last_prompt
    assert "What is the wifi password?" in llm.last_prompt
    assert result.status == "completed"
