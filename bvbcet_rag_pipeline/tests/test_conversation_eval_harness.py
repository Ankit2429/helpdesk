"""Unit tests for Conversation Quality Evaluation Harness."""

from evaluation.conversation_eval_harness import ConversationEvalHarness, ConversationEvalResult


def test_conversation_eval_harness():
    harness = ConversationEvalHarness()

    dummy_engine = lambda q, prompt_version="v2": {
        "answer": "Computer Science offers B.E. programs.",
        "status": "success",
        "filler_stripped": False,
        "metrics": {},
    }

    result = harness.evaluate_engine("v2_grounded_concise", dummy_engine)

    assert isinstance(result, ConversationEvalResult)
    assert result.prompt_version == "v2_grounded_concise"
    assert result.hallucination_rate_pct == 0.0
    assert result.brevity_pass_rate_pct == 100.0
