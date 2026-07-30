"""Unit tests for RAG Evaluation Harness."""

from evaluation.eval_harness import EvalMetricResult, EvaluationHarness


def test_eval_harness_metrics():
    expected_keywords = ["Computer Science", "B.E.", "AI"]
    retrieved_texts = [
        "Computer Science department offers B.E. in Artificial Intelligence.",
        "Hostel fee structure is 60000 INR.",
    ]

    metrics = EvaluationHarness.calculate_retrieval_metrics(
        expected_keywords=expected_keywords,
        retrieved_texts=retrieved_texts,
        k_values=[1, 3, 5],
    )

    assert metrics["mrr"] == 1.0  # Hit at rank 1
    assert metrics["recall_1"] == 1.0
    assert metrics["precision_1"] == 1.0
    assert metrics["precision_3"] == 0.50
