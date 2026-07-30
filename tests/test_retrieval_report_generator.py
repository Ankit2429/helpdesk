# tests/test_retrieval_report_generator.py
"""Tests for the RetrievalReportGenerator module.

These tests cover:
- Successful markdown generation and status calculations
- File write operations with overwrite protection
- Validation of report data
- Error handling for filesystem failures
- End‑to‑end generation of all report artefacts
"""

import json
import tempfile
from pathlib import Path

import pytest

from evaluation.benchmarks.retrieval_metrics import (
    FailedCaseRecord,
    RetrievalAggregateReport,
    RetrievalCategoryMetrics,
    RetrievalItemResult,
)
from evaluation.benchmarks.retrieval_report_generator import (
    ReportGenerationError,
    RetrievalReportGenerator,
)


def build_dummy_report() -> RetrievalAggregateReport:
    items: list[RetrievalItemResult] = []
    for i in range(5):
        items.append(
            RetrievalItemResult(
                item_id=i,
                question=f"Question {i}",
                expected_document="DocA",
                category="cat1",
                difficulty="easy",
                perspective="neutral",
                top1_retrieved="DocA" if i % 2 == 0 else None,
                top3_retrieved=["DocA"] if i % 3 == 0 else [],
                top5_retrieved=["DocA"] if i % 2 == 0 else [],
                retrieved_scores=[0.9],
                retrieval_rank=1 if i % 2 == 0 else 0,
                top1_match=bool(i % 2 == 0),
                top3_match=bool(i % 3 == 0),
                top5_match=bool(i % 2 == 0),
                reciprocal_rank=1.0 if i % 2 == 0 else 0.0,
                latency_ms=10.0 + i,
                failure_reason=None if i % 2 == 0 else "Not found",
            )
        )
    failed_cases = [
        FailedCaseRecord(
            item_id=99,
            question="Failed question",
            expected_document="DocZ",
            category="cat1",
            difficulty="hard",
            perspective="neutral",
            retrieved_documents=[],
            similarity_scores=[],
            retrieval_rank=0,
            failure_reason="No match",
        )
    ]
    cat_metrics = RetrievalCategoryMetrics(
        category="cat1",
        total_queries=5,
        success_count=3,
        failure_count=2,
        success_rate=0.6,
        failure_rate=0.4,
        recall_at_1=0.4,
        recall_at_3=0.2,
        recall_at_5=0.6,
        mrr=0.5,
        mean_latency_ms=12.0,
        median_latency_ms=12.0,
        p95_latency_ms=14.0,
    )
    return RetrievalAggregateReport(
        timestamp="2026-07-29T00:00:00Z",
        total_queries=5,
        overall_success_count=3,
        overall_failure_count=2,
        overall_success_rate=0.6,
        overall_failure_rate=0.4,
        overall_recall_at_1=0.4,
        overall_recall_at_3=0.2,
        overall_recall_at_5=0.6,
        overall_mrr=0.5,
        overall_mean_latency_ms=12.0,
        overall_median_latency_ms=12.0,
        overall_p95_latency_ms=14.0,
        category_breakdown={"cat1": cat_metrics},
        item_results=items,
        failed_cases=failed_cases,
    )


@pytest.fixture
def temp_output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_generate_markdown_success_status(temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()
    md = gen.generate_markdown(report)
    assert "**Success Rate**" in md
    assert "NEEDS OPTIMIZATION" in md
    assert "Recall@1" in md
    assert "NEEDS OPTIMIZATION" in md


def test_save_markdown_overwrite_protection(temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()
    md_path = gen.save_markdown_report(report, filename="test.md", overwrite=False)
    assert md_path.is_file()
    with pytest.raises(FileExistsError):
        gen.save_markdown_report(report, filename="test.md", overwrite=False)
    md_path2 = gen.save_markdown_report(report, filename="test.md", overwrite=True)
    assert md_path2.is_file()


def test_validate_report_invalid_values(temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()
    report.overall_success_rate = 1.5
    with pytest.raises(ValueError, match="out of expected 0-1 range"):
        gen._validate_report(report)
    report.overall_success_rate = 0.6
    report.overall_mean_latency_ms = -10.0
    with pytest.raises(ValueError, match="cannot be negative"):
        gen._validate_report(report)


def test_write_file_os_error(monkeypatch, temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()

    def mock_open(*args, **kwargs):
        raise PermissionError("mock permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(ReportGenerationError) as exc:
        gen.save_json_report(report, filename="broken.json", overwrite=True)
    assert "mock permission denied" in str(exc.value)


def test_generate_all_reports_end_to_end(temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()
    paths = gen.generate_all_reports(report, overwrite=False)
    assert set(paths.keys()) == {"markdown", "json", "failed_cases", "csv"}
    for p in paths.values():
        assert p.is_file()
    json_path = paths["json"]
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["overall_success_rate"] == 0.6
    md_path = paths["markdown"]
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    assert "RAG Vector & Hybrid Retrieval Benchmark Report" in content


def test_smoke_report_generation(temp_output_dir):
    gen = RetrievalReportGenerator(output_dir=temp_output_dir)
    report = build_dummy_report()
    gen.generate_all_reports(report, overwrite=True)
    expected_files = [
        temp_output_dir / "retrieval_report.md",
        temp_output_dir / "retrieval_report.json",
        temp_output_dir / "failed_cases.json",
        temp_output_dir / "summary.csv",
    ]
    for f in expected_files:
        assert f.is_file()
