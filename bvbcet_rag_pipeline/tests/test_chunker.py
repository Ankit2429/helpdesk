"""Comprehensive unit and integration test suite for the Semantic Markdown Chunker."""

import json
from pathlib import Path
import shutil
import tempfile

from chunker.chunker import ChunkerRunner
from chunker.metadata import ChunkMetadataProcessor
from chunker.semantic_chunker import Chunk, SemanticMarkdownChunker


def test_markdown_parsing():
    """Test basic Markdown text parsing into semantic sections."""
    chunker = SemanticMarkdownChunker()
    markdown = "# Title\n\nThis is paragraph content.\n\n## Subheading\n\nMore content here."
    sections = chunker.parse_semantic_sections(Path("test.md"), markdown)
    assert len(sections) == 2
    assert sections[0].heading == "Title"
    assert sections[1].heading == "Subheading"


def test_heading_preservation():
    """Test heading context preservation in generated chunks."""
    chunker = SemanticMarkdownChunker()
    markdown = "# Admissions Guide\n\n## Eligibility Criteria\n\nMust have 60% aggregate marks."
    chunks = chunker.process_text(markdown, Path("admissions.md"))
    assert len(chunks) > 0
    assert "Admissions Guide" in chunks[0].text
    assert "Eligibility Criteria" in chunks[0].text


def test_table_preservation():
    """Test preserving Markdown tables as atomic non-split blocks."""
    chunker = SemanticMarkdownChunker()
    markdown = """# Fee Structure

| Course | Fee (INR) | Duration |
| --- | --- | --- |
| B.E. CSE | 125000 | 4 Years |
| M.Tech VLSI | 95000 | 2 Years |
"""
    sections = chunker.parse_semantic_sections(Path("fees.md"), markdown)
    assert len(sections) == 1
    table_blocks = [b for b in sections[0].blocks if b.block_type == "table"]
    assert len(table_blocks) == 1
    assert "| B.E. CSE | 125000 | 4 Years |" in table_blocks[0].text


def test_code_block_preservation():
    """Test preserving code blocks as atomic non-split blocks."""
    chunker = SemanticMarkdownChunker()
    markdown = """# Code Snippets

```python
def calculate_gpa(marks):
    return sum(marks) / len(marks)
```
"""
    sections = chunker.parse_semantic_sections(Path("code.md"), markdown)
    code_blocks = [b for b in sections[0].blocks if b.block_type == "code"]
    assert len(code_blocks) == 1
    assert "def calculate_gpa" in code_blocks[0].text


def test_chunk_overlap():
    """Test chunk overlap functionality when text exceeds max token limit."""
    chunker = SemanticMarkdownChunker(ideal_tokens=30, max_tokens=40, overlap_tokens=10)
    long_paragraph = "Word " * 200
    markdown = f"# Long Document\n\n{long_paragraph}"

    chunks = chunker.process_text(markdown, Path("long.md"))
    assert len(chunks) > 1


def test_duplicate_removal():
    """Test SHA256 duplicate chunk detection and removal."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        processor = ChunkMetadataProcessor(output_dir=temp_dir)
        chunk1 = Chunk(id="chunk_1", title="Title", heading="H1", level=1, text="Identical content body", token_count=10)
        chunk2 = Chunk(id="chunk_2", title="Title", heading="H1", level=1, text="Identical content body", token_count=10)

        records = processor.process_chunks([chunk1, chunk2], markdown_files_processed=1)
        assert len(records) == 1
    finally:
        shutil.rmtree(temp_dir)


def test_statistics_generation():
    """Test generating statistics.json output metrics."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        processor = ChunkMetadataProcessor(output_dir=temp_dir)
        chunk = Chunk(id="chunk_stat", title="Stat Title", heading="Stat Heading", level=1, text="Sample body text", token_count=8)

        processor.process_chunks([chunk], markdown_files_processed=1)

        stats_path = temp_dir / "statistics.json"
        assert stats_path.exists()

        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)

        assert stats["markdown_files_processed"] == 1
        assert stats["chunks_created"] == 1
        assert stats["duplicates_removed"] == 0
        assert stats["smallest_chunk"] == 8
        assert stats["largest_chunk"] == 8
    finally:
        shutil.rmtree(temp_dir)
