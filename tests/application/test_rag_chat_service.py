"""Unit tests for RAGChatService hallucination guarding and distance threshold checks."""

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder


class DummyLLMService:
    """Records call counts for generate and generate_stream, and captures prompts."""

    def __init__(self) -> None:
        self.called = False
        self.generate_count = 0
        self.generate_stream_count = 0
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.called = True
        self.generate_count += 1
        self.last_prompt = prompt
        return "LLM Generated Response"

    def generate_stream(self, prompt: str):
        self.called = True
        self.generate_stream_count += 1
        self.last_prompt = prompt
        for chunk in ["LLM ", "Streamed ", "Response"]:
            yield chunk


class FakeHighDistancePipeline:
    """Returns a search result with a high FAISS distance score (low similarity)."""

    def search(self, query: str) -> list[SearchResult]:
        doc = KnowledgeDocument(content="Irrelevant document content", metadata={})
        # Distance 2.5 > threshold 1.0
        return [SearchResult(document=doc, distance=2.5)]


class FakeValidPipeline:
    """Returns a valid search result within distance threshold."""

    def search(self, query: str) -> list[SearchResult]:
        doc = KnowledgeDocument(content="Valid campus information", metadata={"source": "faq.md"})
        return [SearchResult(document=doc, distance=0.2)]


def test_rag_chat_service_falls_back_to_llm_on_high_distance() -> None:
    """When RAG results exceed the distance threshold, the LLM should still be called
    with a general knowledge prompt rather than returning a dead-end fallback."""
    llm = DummyLLMService()
    pipeline = FakeHighDistancePipeline()
    context_builder = PromptContextBuilder(similarity_threshold=1.0)
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline, context_builder=context_builder)

    result = service.respond("What is the wifi password?")

    assert llm.called
    assert llm.generate_count == 1
    assert llm.generate_stream_count == 0
    assert "Context:" not in llm.last_prompt
    assert "What is the wifi password?" in llm.last_prompt
    assert result.status == "completed"


def test_respond_stream_executes_generation_once_without_context() -> None:
    """When RAG context is unavailable, respond_stream should call generate_stream exactly once
    and must not make a duplicate call to generate."""
    llm = DummyLLMService()
    pipeline = FakeHighDistancePipeline()
    context_builder = PromptContextBuilder(similarity_threshold=1.0)
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline, context_builder=context_builder)

    tokens = list(service.respond_stream("Hello", session_id="s1"))

    assert tokens == ["LLM ", "Streamed ", "Response"]
    assert llm.generate_stream_count == 1
    assert llm.generate_count == 0

    # Verify response is recorded in session memory
    messages = service.session_manager.get_or_create_session("s1").get_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "Hello"
    assert messages[1]["content"] == "LLM Streamed Response"


def test_respond_stream_executes_generation_once_with_context() -> None:
    """When RAG context is available, respond_stream should call generate_stream exactly once
    and must not call generate."""
    llm = DummyLLMService()
    pipeline = FakeValidPipeline()
    context_builder = PromptContextBuilder(similarity_threshold=1.0)
    service = RAGChatService(llm_service=llm, rag_pipeline=pipeline, context_builder=context_builder)

    tokens = list(service.respond_stream("Campus info", session_id="s2"))

    assert tokens == ["LLM ", "Streamed ", "Response"]
    assert llm.generate_stream_count == 1
    assert llm.generate_count == 0

    # Verify response is recorded in session memory
    messages = service.session_manager.get_or_create_session("s2").get_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "Campus info"
    assert messages[1]["content"] == "LLM Streamed Response"

