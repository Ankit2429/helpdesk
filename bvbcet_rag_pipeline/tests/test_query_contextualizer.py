"""Unit tests for Query Contextualizer and Session Cache."""

from conversation_manager.query_contextualizer import ContextualizedQueryOutput, QueryContextualizer


def test_query_contextualizer():
    contextualizer = QueryContextualizer(cache_ttl_turns=3)

    context = [
        {
            "question": "Where is Computer Science department located?",
            "answer": "Computer Science department is located in B-Block.",
        }
    ]

    out1 = contextualizer.contextualize_query("What courses does it offer?", conversation_context=context)

    assert isinstance(out1, ContextualizedQueryOutput)
    assert out1.needs_new_retrieval is True
    assert "Computer Science" in out1.contextualized_query or "B-Block" in out1.contextualized_query

    # Test cache insertion & hit
    dummy_chunks = [{"text": "Sample course list", "score": 0.90}]
    contextualizer.cache_retrieval_result(out1.contextualized_query, dummy_chunks)

    out2 = contextualizer.contextualize_query("What courses does it offer?", conversation_context=context)
    assert out2.needs_new_retrieval is False
    assert len(out2.cached_chunks) == 1
