"""Unit tests for BVBCET RAG Pipeline modules."""

from pathlib import Path
from chunker.chunker import ChunkerRunner
from chunker.semantic_chunker import SemanticMarkdownChunker


def test_semantic_chunker_instance():
    chunker = SemanticMarkdownChunker(ideal_tokens=500, max_tokens=800, overlap_tokens=100)
    assert chunker.max_tokens == 800


def test_chunker_runner_instance():
    runner = ChunkerRunner(input_dir=Path("knowledge_base/markdown"))
    assert runner.chunk_size == 750
