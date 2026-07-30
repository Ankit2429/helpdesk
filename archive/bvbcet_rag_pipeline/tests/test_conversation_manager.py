"""Unit and integration tests for ConversationManager."""

from unittest.mock import MagicMock
from langchain_core.documents import Document

from conversation.conversation_manager import ConversationManager
from conversation.intent_classifier import Intent
from llm.inference import LocalLLMInference


def test_conversation_manager_canned_intent():
    manager = ConversationManager()
    resp = manager.handle("Hello!")

    assert resp.intent == Intent.GREETING
    assert "Welcome to KLE" in resp.answer
    assert resp.status == "direct_canned_response"


def test_conversation_manager_question_flow():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = ("Computer Science offers B.E. degrees.", 0.5, None)

    manager = ConversationManager(
        llm_inference=LocalLLMInference(backend=mock_backend)
    )

    dummy_doc = Document(
        page_content="Computer Science Department offers B.E. and M.Tech programs.",
        metadata={"id": "doc_1", "source": "cs.md", "heading": "Overview", "score": 0.90},
    )
    manager.retriever.retrieve = MagicMock(return_value=[dummy_doc])

    resp = manager.handle("What courses does Computer Science offer?")

    assert resp.intent == Intent.QUESTION
    assert resp.status in ["success", "hallucination_flagged"]
    assert len(resp.citations) == 1
    assert resp.citations[0]["source"] == "cs.md"
