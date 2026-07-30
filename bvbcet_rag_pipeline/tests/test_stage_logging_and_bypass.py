"""Unit tests verifying ChromaDB retrieval bypass and standalone query rewriting."""

from unittest.mock import MagicMock
from langchain_core.documents import Document

from conversation.conversation_manager import ConversationManager
from conversation.intent_classifier import Intent


def test_greetings_bypass_retriever():
    mock_retriever = MagicMock()
    manager = ConversationManager(retriever=mock_retriever, verbose_logging=False)

    resp = manager.handle("hi")

    assert resp.intent == Intent.GREETING
    assert "Welcome to KLE" in resp.answer
    assert resp.status == "direct_canned_response"
    mock_retriever.retrieve.assert_not_called()


def test_thanks_bypass_retriever():
    mock_retriever = MagicMock()
    manager = ConversationManager(retriever=mock_retriever, verbose_logging=False)

    resp = manager.handle("thank you so much!")

    assert resp.intent == Intent.THANKS
    assert "welcome" in resp.answer.lower()
    assert resp.status == "direct_canned_response"
    mock_retriever.retrieve.assert_not_called()


def test_goodbye_bypass_retriever():
    mock_retriever = MagicMock()
    manager = ConversationManager(retriever=mock_retriever, verbose_logging=False)

    resp = manager.handle("bye take care")

    assert resp.intent == Intent.GOODBYE
    assert "Goodbye" in resp.answer
    assert resp.status == "direct_canned_response"
    mock_retriever.retrieve.assert_not_called()


def test_followup_question_query_rewriting():
    mock_retriever = MagicMock()
    dummy_doc = Document(page_content="KLE Tech was founded by BVB.", metadata={"source": "bvb.md"})
    mock_retriever.retrieve.return_value = [dummy_doc]

    mock_backend = MagicMock()
    mock_backend.generate.return_value = ("KLE Tech was founded by BVB.", 0.2, None)

    manager = ConversationManager(retriever=mock_retriever, verbose_logging=False)
    manager.llm_inference.generate = mock_backend.generate

    # Turn 1: Primary query
    manager.handle("Tell me about KLE Tech")

    # Turn 2: Follow-up query with pronoun
    resp = manager.handle("Who founded it?")

    assert resp.intent == Intent.QUESTION
    assert resp.resolved_query == "Who founded KLE Tech?"
    mock_retriever.retrieve.assert_called_with(
        question="Who founded KLE Tech?",
        top_k=5,
        score_threshold=0.35,
        rerank=True,
    )
