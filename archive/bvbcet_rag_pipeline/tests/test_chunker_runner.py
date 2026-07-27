"""Unit tests for ChunkerRunner CLI and workflow."""

from pathlib import Path
import shutil
import tempfile
from chunker.chunker import ChunkerRunner


def test_chunker_runner_workflow():
    temp_input = Path(tempfile.mkdtemp())
    temp_output = Path(tempfile.mkdtemp())

    try:
        # Create dummy Markdown files
        doc1 = temp_input / "doc1.md"
        doc1.write_text("# Doc 1\n\n**Source URL:** https://kletech.ac.in/doc1\n\nThis is document 1 content.", encoding="utf-8")

        sub_dir = temp_input / "subfolder"
        sub_dir.mkdir(parents=True, exist_ok=True)
        doc2 = sub_dir / "doc2.md"
        doc2.write_text("# Doc 2\n\n**Source URL:** https://kletech.ac.in/doc2\n\nThis is document 2 content.", encoding="utf-8")

        runner = ChunkerRunner(
            input_dir=temp_input,
            output_dir=temp_output,
            chunk_size=500,
            chunk_overlap=50,
        )

        records = runner.run()
        assert len(records) == 2
        assert (temp_output / "chunks.jsonl").exists()
        assert (temp_output / "duplicate_chunks.json").exists()
        assert (temp_output / "statistics.json").exists()

    finally:
        shutil.rmtree(temp_input)
        shutil.rmtree(temp_output)
