"""Centralized RAG Configuration Engine.

Manages parameters for chunking variants, embedding models, vector storage,
BM25 + Dense hybrid search (RRF), Cross-Encoder re-ranking, and dynamic thresholds.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

from config.config import BASE_DIR, CHROMA_DIR, DEFAULT_COLLECTION_NAME


@dataclass
class ChunkerConfig:
    """Configuration for structure-aware semantic chunking."""

    default_chunk_size: int = 512
    default_overlap_pct: float = 0.15  # 15% overlap
    variant_sizes: list[int] = field(default_factory=lambda: [256, 512, 1024])
    content_type_map: dict[str, int] = field(
        default_factory=lambda: {
            "faq": 256,
            "short": 256,
            "narrative": 512,
            "department": 512,
            "regulation": 1024,
            "syllabus": 1024,
        }
    )


@dataclass
class EmbeddingConfig:
    """Configuration for vector embedding generation and caching."""

    primary_model: str = "all-MiniLM-L6-v2"
    multilingual_model: str = "intfloat/multilingual-e5-base"
    normalize_embeddings: bool = True
    batch_size: int = 64
    cache_dir: Path = BASE_DIR / "embeddings" / "cache"
    enable_cache: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for Hybrid Search (RRF), Re-Ranking, and Thresholding."""

    top_k_candidates: int = 20
    top_k_final: int = 5
    score_threshold: float = 0.35
    enable_hybrid: bool = True
    rrf_k: int = 60
    bm25_weight: float = 0.5
    dense_weight: float = 0.5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_reranker: bool = True


@dataclass
class RAGPipelineConfig:
    """Master configuration container for the entire RAG pipeline."""

    chunker: ChunkerConfig = field(default_factory=ChunkerConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    chroma_dir: Path = CHROMA_DIR
    collection_name: str = DEFAULT_COLLECTION_NAME

    @classmethod
    def load_defaults(cls) -> "RAGPipelineConfig":
        """Load default configuration instance."""
        return cls()


# Default global instance
DEFAULT_RAG_CONFIG = RAGPipelineConfig.load_defaults()
