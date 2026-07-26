"""Unit tests for ChunkMetadataProcessor and storage engine."""

from pathlib import Path
import shutil
import tempfile
import json

from chunker.semantic_chunker import Chunk
from chunker.metadata import ChunkMetadataProcessor, ChunkMetadata, ChunkRecord


def test_chunk_metadata_processor():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        processor = ChunkMetadataProcessor(output_dir=temp_dir)

        chunk1 = Chunk(
            id="test_doc_0_0",
            title="Test Title",
            heading="Introduction",
            level=2,
            text="# Test Title\n\n**Source URL:** https://www.kletech.ac.in/test\n\nThis is sample text.",
            token_count=15,
        )

        chunk2 = Chunk(
            id="test_doc_0_1",
            title="Test Title",
            heading="Introduction",
            level=2,
            text="# Test Title\n\n**Source URL:** https://www.kletech.ac.in/test\n\nThis is sample text.",
            token_count=15,
        )

        records = processor.process_chunks([chunk1, chunk2], markdown_files_processed=1)

        # Duplicate detection: chunk2 should be skipped
        assert len(records) == 1
        assert records[0].metadata.id == "test_doc_0_0"
        assert records[0].metadata.url == "https://www.kletech.ac.in/test"
        assert records[0].metadata.sha256_hash is not None

        # Verify chunks.jsonl
        assert (temp_dir / "chunks.jsonl").exists()
        with open(temp_dir / "chunks.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert "text" in data
            assert "metadata" in data
            assert data["metadata"]["title"] == "Test Title"

        # Verify duplicate_chunks.json
        assert (temp_dir / "duplicate_chunks.json").exists()
        with open(temp_dir / "duplicate_chunks.json", "r", encoding="utf-8") as f:
            dups = json.load(f)
            assert len(dups) == 1
            assert dups[0]["chunk_id"] == "test_doc_0_1"

        # Verify statistics.json
        assert (temp_dir / "statistics.json").exists()
        with open(temp_dir / "statistics.json", "r", encoding="utf-8") as f:
            stats = json.load(f)
            assert stats["markdown_files_processed"] == 1
            assert stats["chunks_created"] == 1
            assert stats["duplicates_removed"] == 1

    finally:
        shutil.rmtree(temp_dir)
