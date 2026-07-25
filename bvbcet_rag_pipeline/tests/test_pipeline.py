"""Unit tests for BVBCET RAG Pipeline modules."""

from cleaner.cleaner import TextCleaner
from chunker.chunker import TextChunker
from langchain_core.documents import Document


def test_cleaner():
    raw_text = "Hello\r\nWorld!\n\n\n\nTest   "
    cleaned = TextCleaner.clean_text(raw_text)
    assert "Hello\nWorld!" in cleaned
    assert "\n\n\n" not in cleaned


def test_chunker():
    doc = Document(page_content="A " * 500, metadata={"source": "test"})
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_documents([doc])
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 120 for c in chunks)
