"""Unit tests for QueryRewriter."""

from conversation.memory import ChatMessage
from conversation.query_rewriter import QueryRewriter


def test_query_rewriter_standalone():
    rewriter = QueryRewriter()
    history = [
        ChatMessage(role="user", content="What is KLE Tech?"),
        ChatMessage(role="assistant", content="KLE Tech is a university."),
    ]
    query = "When do KCET admissions start?"
    res = rewriter.rewrite(query, history)
    assert res == "When do KCET admissions start?"


def test_query_rewriter_pronoun():
    rewriter = QueryRewriter()
    history = [
        ChatMessage(role="user", content="Tell me about KLE Tech"),
        ChatMessage(role="assistant", content="KLE Tech was established in Hubballi."),
    ]
    query = "Who founded it?"
    res = rewriter.rewrite(query, history)
    assert "KLE Tech" in res


def test_query_rewriter_short_followup():
    rewriter = QueryRewriter()
    history = [
        ChatMessage(role="user", content="Tell me about hostel"),
        ChatMessage(role="assistant", content="Hostels are available on campus."),
    ]
    query = "Fees?"
    res = rewriter.rewrite(query, history)
    assert "fees" in res.lower()
    assert "hostel" in res.lower()
