"""Vector DB package initialization."""

from vector_db.chroma_builder import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_PERSIST_DIR as DEFAULT_CHROMA_DIR,
    ChromaBuilder,
)
from vector_db.faiss_builder import (
    DEFAULT_PERSIST_DIR as DEFAULT_FAISS_DIR,
    FAISSBuilder,
    main as faiss_main,
)
from vector_db.vector_db import VectorDBManager

__all__ = [
    "VectorDBManager",
    "ChromaBuilder",
    "FAISSBuilder",
    "DEFAULT_COLLECTION_NAME",
    "DEFAULT_CHROMA_DIR",
    "DEFAULT_FAISS_DIR",
    "faiss_main",
]
