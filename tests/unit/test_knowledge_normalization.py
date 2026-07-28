"""Unit tests for the Knowledge Normalization Pipeline."""

import tempfile
from pathlib import Path

import pytest
from campus_helpdesk.infrastructure.knowledge.duplicate_detector import DuplicateDetector
from campus_helpdesk.infrastructure.knowledge.metadata_extractor import MetadataExtractor
from campus_helpdesk.infrastructure.knowledge.pipeline import KnowledgeNormalizationPipeline
from campus_helpdesk.infrastructure.knowledge.text_cleaner import MarkdownTextCleaner


def test_markdown_text_cleaner():
    cleaner = MarkdownTextCleaner()
    raw = "# Title\r\n\r\nThis is paragraph 1.<br>\n\n\n\nThis is paragraph 2.   "
    cleaned = cleaner.clean(raw)

    assert "\r" not in cleaned
    assert "<br>" not in cleaned
    assert "  " not in cleaned
    assert "# Title\n\nThis is paragraph 1.\n\nThis is paragraph 2." in cleaned


def test_metadata_extractor():
    extractor = MetadataExtractor()
    content = "# Central Library Guide\n\nThe library is open daily."
    metadata = extractor.extract(content, source_path=Path("library_guide.md"))

    assert metadata["title"] == "Central Library Guide"
    assert metadata["category"] == "general"
    assert metadata["word_count"] > 0
    assert "sha256" in metadata
    assert "processed_at" in metadata


def test_duplicate_detector():
    detector = DuplicateDetector()
    text1 = "Sample campus schedule document."
    text2 = "Sample campus schedule document."
    text3 = "Different document text."

    assert not detector.is_duplicate(text1)
    detector.register(text1)

    assert detector.is_duplicate(text2)
    assert not detector.is_duplicate(text3)
    assert detector.total_seen == 1


def test_normalization_pipeline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = Path(tmp_dir) / "raw"
        canonical_dir = Path(tmp_dir) / "canonical"
        raw_dir.mkdir()

        test_file = raw_dir / "admissions.md"
        test_file.write_text("# Admissions Info\n\nApply via online portal.\n", encoding="utf-8")

        pipeline = KnowledgeNormalizationPipeline(raw_dir=raw_dir, canonical_dir=canonical_dir)
        summary = pipeline.process_directory()

        assert summary["total_files_scanned"] == 1
        assert summary["canonical_processed"] == 1
        assert summary["duplicates_skipped"] == 0

        output_file = canonical_dir / "admissions.md"
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "---" in content
        assert "title: Admissions Info" in content
        assert "Apply via online portal." in content
