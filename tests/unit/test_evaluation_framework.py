"""Unit tests for RAG Evaluation Framework (metrics, dataset loading, and report generation)."""

from pathlib import Path

from campus_helpdesk.infrastructure.evaluation.metrics import (
    calculate_keyword_coverage,
    calculate_mrr,
    calculate_recall_at_k,
)
from campus_helpdesk.infrastructure.evaluation.runner import EvaluationRunner


def test_metric_recall_at_k():
    retrieved = ["doc_a.md", "doc_b.md", "doc_c.md"]
    expected = ["doc_b.md"]

    assert calculate_recall_at_k(retrieved, expected, k=1) == 0.0
    assert calculate_recall_at_k(retrieved, expected, k=2) == 1.0


def test_metric_mrr():
    retrieved = ["doc_a.md", "doc_b.md", "doc_c.md"]
    expected = ["doc_b.md"]

    # doc_b is at rank 2 -> MRR = 1/2 = 0.5
    assert calculate_mrr(retrieved, expected) == 0.5


def test_metric_keyword_coverage():
    text = "The Central Library is located in Block C, 2nd floor."
    keywords = ["Block C", "2nd floor", "Basement"]

    ratio, matched, missing = calculate_keyword_coverage(text, keywords)
    assert ratio == 2 / 3
    assert "Block C" in matched
    assert "Basement" in missing


def test_evaluation_runner_dataset_loading(tmp_path):
    dataset_file = tmp_path / "questions.yaml"
    dataset_file.write_text(
        """questions:
  - id: TEST01
    category: Test
    question: "Where is the library?"
    expected_answer_keywords: ["Block C"]
    expected_sources: ["lib.md"]
"""
    )

    class DummyPipeline:
        pass

    runner = EvaluationRunner(DummyPipeline(), dataset_path=dataset_file, output_dir=tmp_path)
    questions = runner.load_dataset()

    assert len(questions) == 1
    assert questions[0]["id"] == "TEST01"
