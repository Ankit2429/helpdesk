"""Unit tests for SemanticMarkdownChunker."""

from pathlib import Path
from chunker.semantic_chunker import Chunk, SemanticMarkdownChunker


def test_chunker_basic():
    chunker = SemanticMarkdownChunker()
    markdown = """# Main Document Title

## Introduction
This is the introduction section. It contains some basic details about the university campus.

## Department Table
| Department | Code | Location |
| --- | --- | --- |
| Computer Science | CSE | Block B |
| Electrical | EEE | Block A |

## Code Examples
```python
def hello_world():
    print("Hello from KLE Tech!")
```

> Important notice: Attendance is mandatory.
"""

    file_path = Path("test_document.md")
    sections = chunker.parse_semantic_sections(file_path, markdown)
    assert len(sections) >= 3

    chunks = chunker.process_text(markdown, file_path)
    assert len(chunks) > 0
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].title is not None
    assert chunks[0].heading is not None
    assert chunks[0].level >= 1
    assert chunks[0].token_count > 0


def test_atomic_blocks_integrity():
    chunker = SemanticMarkdownChunker()
    raw_lines = [
        "| Col1 | Col2 |",
        "| --- | --- |",
        "| Val1 | Val2 |",
        "",
        "- List Item 1",
        "- List Item 2",
        "",
        "```python",
        "x = 10",
        "```",
    ]
    blocks = chunker.parse_blocks(raw_lines)
    types = [b.block_type for b in blocks]
    assert types == ["table", "list", "code"]
