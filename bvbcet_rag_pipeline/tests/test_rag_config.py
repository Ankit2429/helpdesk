"""Unit tests for RAG configuration module."""

from config.rag_config import RAGPipelineConfig, DEFAULT_RAG_CONFIG


def test_rag_config_defaults():
    config = RAGPipelineConfig.load_defaults()

    assert config.chunker.default_chunk_size == 512
    assert config.chunker.default_overlap_pct == 0.15
    assert 256 in config.chunker.variant_sizes
    assert config.embedding.primary_model == "all-MiniLM-L6-v2"
    assert config.retrieval.enable_hybrid is True
    assert config.retrieval.rrf_k == 60
    assert config.retrieval.enable_reranker is True
