"""Unit tests for advanced semantic chunker."""

from pathlib import Path
from chunker.semantic_chunker import Chunk, SemanticMarkdownChunker


def test_semantic_chunker_adaptive_sizes():
    chunker_256 = SemanticMarkdownChunker(ideal_tokens=256, max_tokens=300, overlap_pct=0.15)
    chunker_512 = SemanticMarkdownChunker(ideal_tokens=512, max_tokens=600, overlap_pct=0.15)

    sample_md = """# Department of Computer Science

## Programs Offered
The Department of Computer Science and Engineering offers B.E. in Artificial Intelligence, B.E. in Computer Science, and M.Tech programs.
Students learn software engineering, machine learning, cloud computing, algorithms, database systems, and networking.

## Admissions Criteria
Candidates applying for B.E. programs must appear for KCET or COMEDK competitive examinations.
Selection is based on state merit ranking and counseling rounds.
"""

    dummy_path = Path("markdown/departments/computer_science.md")
    chunks_256 = chunker_256.process_text(sample_md, dummy_path)
    chunks_512 = chunker_512.process_text(sample_md, dummy_path)

    assert len(chunks_256) > 0
    assert len(chunks_512) > 0
    assert isinstance(chunks_512[0], Chunk)
    assert chunks_512[0].source_doc == "computer_science.md"
    assert chunks_512[0].word_count > 0
    assert chunks_512[0].language == "en"
