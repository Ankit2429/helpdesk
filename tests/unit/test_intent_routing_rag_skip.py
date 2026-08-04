"""Unit tests for Intent Routing RAG bypass in RAGChatService."""

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder


class SpyRAGPipeline:
    """Mock RAG pipeline that records calls to search()."""

    def __init__(self) -> None:
        self.search_called = False
        self.queries: list[str] = []

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.search_called = True
        self.queries.append(query)
        # Default return with high distance (low confidence) to trigger threshold check
        doc = KnowledgeDocument(content="Some campus info", metadata={})
        return [SearchResult(document=doc, distance=2.0)]


class MockLLMService:
    def __init__(self) -> None:
        self.called = False

    def generate(self, prompt: str) -> str:
        self.called = True
        return "Conversational Response"

    def generate_stream(self, prompt: str):
        self.called = True
        yield "Conversational Response"


def test_conversational_intents_bypass_rag() -> None:
    """Verify that greetings, small talk, thanks, and goodbye queries skip RAG search."""
    conversational_queries = [
        "hi",
        "hello",
        "thanks",
        "bye",
        "how are you",
    ]

    for query in conversational_queries:
        pipeline = SpyRAGPipeline()
        llm = MockLLMService()
        service = RAGChatService(llm_service=llm, rag_pipeline=pipeline)

        # 1. Test non-streaming respond()
        res = service.respond(query)
        assert not pipeline.search_called, f"RAG was called for query: '{query}' in respond()"
        assert res.reply is not None
        assert res.reply != "I couldn't find reliable information about that. Could you rephrase your question?"

        # 2. Test streaming respond_stream()
        pipeline_stream = SpyRAGPipeline()
        llm_stream = MockLLMService()
        service_stream = RAGChatService(llm_service=llm_stream, rag_pipeline=pipeline_stream)

        tokens = list(service_stream.respond_stream(query))
        assert not pipeline_stream.search_called, f"RAG was called for query: '{query}' in respond_stream()"
        assert len(tokens) > 0
        assert tokens[0] != "I couldn't find reliable information about that. Could you rephrase your question?"


def test_campus_query_invokes_rag() -> None:
    """Verify that campus query (e.g. principal or fees) invokes RAG search."""
    pipeline = SpyRAGPipeline()
    llm = MockLLMService()
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline)

    res = service.respond("who is the vice chancellor of kle tech?")
    assert pipeline.search_called, "RAG search was not called for campus query"
