"""Unit tests for production CanonicalIndexBuilder."""

import json
import tempfile
from pathlib import Path

import pytest
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.canonical_index_builder import CanonicalIndexBuilder
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker


class DummyEmbeddings:
    """Mock embeddings generating deterministic 384-dim vectors for testing."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 384


def test_canonical_index_builder_end_to_end():
    from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore

    with tempfile.TemporaryDirectory() as tmp_dir:
        root_path = Path(tmp_dir)
        canonical_dir = root_path / "canonical_markdown"
        index_dir = root_path / "faiss_index"

        canonical_dir.mkdir()
        doc1 = canonical_dir / "library.md"
        doc1.write_text("# Central Library\n\nOpen Mon-Sat 8AM to 8PM.\n", encoding="utf-8")

        loader = KnowledgeLoader(knowledge_source_path=canonical_dir, max_file_size_bytes=1024 * 1024)
        chunker = SemanticDocumentChunker(chunk_size=500, chunk_overlap=50)
        embeddings = DummyEmbeddings()
        store = FAISSSimilarityStore(
            embeddings=embeddings,
            index_path=index_dir,
            allow_dangerous_deserialization=True,
            embedding_metadata={"embedding_model": "mock-model", "embedding_normalize": True},
        )

        builder = CanonicalIndexBuilder(
            loader=loader,
            chunker=chunker,
            similarity_store=store,
            canonical_dir=canonical_dir,
        )

        stats = builder.build_index()

        assert stats["documents_processed"] == 1
        assert stats["chunks_created"] >= 1
        assert stats["errors_count"] == 0

        # Verify index-manifest.json
        manifest_file = index_dir / "index-manifest.json"
        assert manifest_file.exists()

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest["pipeline_version"] == "1.0.0"
        assert manifest["embedding_model"] == "mock-model"
        assert manifest["faiss_index_type"] == "FAISS_FlatL2"
        assert manifest["number_of_documents"] == 1
        assert "library.md" in manifest["document_hashes"]


def test_canonical_index_builder_incremental_build():
    from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore

    with tempfile.TemporaryDirectory() as tmp_dir:
        root_path = Path(tmp_dir)
        canonical_dir = root_path / "canonical_markdown"
        index_dir = root_path / "faiss_index"

        canonical_dir.mkdir()
        doc1 = canonical_dir / "admissions.md"
        doc1.write_text("# Admissions Guide\n\nApply online at college portal.\n", encoding="utf-8")

        loader = KnowledgeLoader(knowledge_source_path=canonical_dir, max_file_size_bytes=1024 * 1024)
        chunker = SemanticDocumentChunker(chunk_size=500, chunk_overlap=50)
        embeddings = DummyEmbeddings()
        store = FAISSSimilarityStore(
            embeddings=embeddings,
            index_path=index_dir,
            allow_dangerous_deserialization=True,
            embedding_metadata={"embedding_model": "mock-model", "embedding_normalize": True},
        )

        builder = CanonicalIndexBuilder(
            loader=loader,
            chunker=chunker,
            similarity_store=store,
            canonical_dir=canonical_dir,
        )

        # Initial build
        stats1 = builder.build_index()
        assert stats1["documents_processed"] == 1
        assert stats1["duplicates_skipped"] == 0

        # Incremental second build without changes
        stats2 = builder.build_index()
        assert stats2["documents_processed"] == 0
        assert stats2["duplicates_skipped"] == 1


def test_canonical_index_builder_error_resilience():
    from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore

    with tempfile.TemporaryDirectory() as tmp_dir:
        root_path = Path(tmp_dir)
        canonical_dir = root_path / "canonical_markdown"
        index_dir = root_path / "faiss_index"

        canonical_dir.mkdir()
        good_doc = canonical_dir / "good.md"
        good_doc.write_text("# Valid Document\n\nValid contents here.\n", encoding="utf-8")

        empty_doc = canonical_dir / "empty.md"
        empty_doc.write_text("", encoding="utf-8")

        loader = KnowledgeLoader(knowledge_source_path=canonical_dir, max_file_size_bytes=1024 * 1024)
        chunker = SemanticDocumentChunker(chunk_size=500, chunk_overlap=50)
        embeddings = DummyEmbeddings()
        store = FAISSSimilarityStore(
            embeddings=embeddings,
            index_path=index_dir,
            allow_dangerous_deserialization=True,
            embedding_metadata={"embedding_model": "mock-model", "embedding_normalize": True},
        )

        builder = CanonicalIndexBuilder(
            loader=loader,
            chunker=chunker,
            similarity_store=store,
            canonical_dir=canonical_dir,
        )

        stats = builder.build_index()
        assert stats["documents_processed"] == 1
        assert stats["empty_documents_skipped"] == 1
