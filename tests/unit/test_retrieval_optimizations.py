"""Unit tests for retrieval optimizations (Document Deduplication & Candidate Window Expansion)."""

import unittest
from unittest.mock import MagicMock

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.application.rag_pipeline import RAGPipeline


class TestRetrievalOptimizations(unittest.TestCase):
    """Test suite for Top-K Document Deduplication and Candidate Window Expansion."""

    def test_settings_retrieval_configuration(self):
        """Verify settings support candidate_window, final_top_k, and deduplicate_documents."""
        settings = Settings()
        self.assertEqual(settings.candidate_window, 25)
        self.assertEqual(settings.final_top_k, 4)
        self.assertTrue(settings.deduplicate_documents)
        self.assertEqual(settings.reranker_top_n, 25)
        self.assertEqual(settings.reranker_top_m, 5)

    def test_rag_pipeline_deduplication(self):
        """Verify that RAGPipeline.search deduplicates chunks from the same source document."""
        mock_loader = MagicMock()
        mock_chunker = MagicMock()
        mock_store = MagicMock()

        # Create mock search results with duplicate source filenames
        doc1_a = KnowledgeDocument(content="Chunk 1 content", metadata={"source_filename": "doc1.md"})
        doc1_b = KnowledgeDocument(content="Chunk 2 content", metadata={"source_filename": "doc1.md"})
        doc2_a = KnowledgeDocument(content="Chunk 3 content", metadata={"source_filename": "doc2.md"})
        doc3_a = KnowledgeDocument(content="Chunk 4 content", metadata={"source_filename": "doc3.md"})

        candidates = [
            SearchResult(document=doc1_a, distance=0.1),
            SearchResult(document=doc1_b, distance=0.2),  # Duplicate doc1
            SearchResult(document=doc2_a, distance=0.3),
            SearchResult(document=doc3_a, distance=0.4),
        ]

        mock_store.search.return_value = candidates

        pipeline = RAGPipeline(
            document_loader=mock_loader,
            document_chunker=mock_chunker,
            similarity_store=mock_store,
            search_limit=5,
            reranker=None,
            reranker_top_n=25,
            deduplicate_documents=True,
        )

        results = pipeline.search("admission", limit=5)
        result_sources = [r.document.metadata["source_filename"] for r in results]

        # Verify no duplicate source filenames
        self.assertEqual(result_sources, ["doc1.md", "doc2.md", "doc3.md"])
        self.assertEqual(len(result_sources), len(set(result_sources)))

    def test_rag_pipeline_candidate_expansion(self):
        """Verify that RAGPipeline requests candidate_window (25) candidates from similarity store."""
        mock_loader = MagicMock()
        mock_chunker = MagicMock()
        mock_store = MagicMock()
        mock_reranker = MagicMock()

        mock_store.search.return_value = []
        mock_reranker.rerank.return_value = []

        pipeline = RAGPipeline(
            document_loader=mock_loader,
            document_chunker=mock_chunker,
            similarity_store=mock_store,
            search_limit=5,
            reranker=mock_reranker,
            reranker_top_n=25,
            deduplicate_documents=True,
        )

        pipeline.search("admission query", limit=5)

        # Verify initial search limit requested is 25 candidates
        mock_store.search.assert_called_once_with("admission query", limit=25)


if __name__ == "__main__":
    unittest.main()
