"""Embeddings package initialization."""

from embeddings.embedding_generator import (
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    EmbeddingGenerator,
    EmbeddingStatistics,
    main,
)

__all__ = [
    "EmbeddingGenerator",
    "EmbeddingStatistics",
    "DEFAULT_MODEL",
    "SUPPORTED_MODELS",
    "main",
]
