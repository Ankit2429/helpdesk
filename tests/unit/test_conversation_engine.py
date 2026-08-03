"""Unit tests for ConversationManager, QueryRewriter, and multi-turn chat memory."""

from campus_helpdesk.application.conversation_manager import ConversationManager
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.domain.conversation import ChatMessage


def test_conversation_manager_history_and_trimming():
    mgr = ConversationManager(max_history_turns=2)

    # Add 3 turns (6 messages)
    mgr.add_user_message("Q1")
    mgr.add_assistant_message("A1")
    mgr.add_user_message("Q2")
    mgr.add_assistant_message("A2")
    mgr.add_user_message("Q3")
    mgr.add_assistant_message("A3")

    history = mgr.get_recent_history()

    # Max history turns = 2, so only 4 latest messages retained
    assert len(history) == 4
    assert history[0].content == "Q2"
    assert history[3].content == "A3"


def test_conversation_manager_reset():
    mgr = ConversationManager(max_history_turns=5)
    mgr.add_user_message("Hello")
    mgr.add_assistant_message("Hi")

    assert len(mgr.get_recent_history()) == 2

    mgr.reset_session("default")
    assert len(mgr.get_recent_history()) == 0


def test_query_rewriter_standalone_rewriting():
    rewriter = QueryRewriter()

    history = [
        ChatMessage(role="user", content="Where is the Central Library located?"),
        ChatMessage(role="assistant", content="The Central Library is located in Block C, 2nd floor."),
    ]

    # Follow-up question with pronoun "its"
    q1 = "What are its operating hours?"
    rw1 = rewriter.rewrite(q1, history)
    assert "Central Library" in rw1
    assert "its" not in rw1

    # Short fragment follow-up question with pronoun
    q2 = "What about its timings?"
    rw2 = rewriter.rewrite(q2, history)
    assert "Central Library" in rw2


def test_query_rewriter_independent_query():
    rewriter = QueryRewriter()
    history = [
        ChatMessage(role="user", content="Where is the Central Library?"),
        ChatMessage(role="assistant", content="In Block C, 2nd floor."),
    ]

    # Standalone query without pronouns
    q = "How do I apply for B.E. Computer Science admissions?"
    rw = rewriter.rewrite(q, history)
    assert rw == q
