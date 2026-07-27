"""Vector DB Manager module for building, persisting, and querying FAISS indices."""

import logging
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class VectorDBManager:
    """FAISS Vector database manager for index building and similarity search."""

    def __init__(self, db_dir: Path, embeddings) -> None:
        self.db_dir = db_dir
        self.embeddings = embeddings

    def build_and_save(self, documents: list[Document], index_name: str = "bvbcet_index") -> FAISS:
        """Create FAISS vector store from document chunks and save to disk."""
        logger.info(f"Building FAISS index with {len(documents)} document chunks...")
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        index_path = self.db_dir / index_name
        vectorstore.save_local(str(index_path))
        logger.info(f"FAISS index successfully saved to '{index_path}'")
        return vectorstore

    def load_index(self, index_name: str = "bvbcet_index") -> FAISS | None:
        """Load existing FAISS vector store from disk."""
        index_path = self.db_dir / index_name
        if index_path.exists():
            try:
                return FAISS.load_local(
                    str(index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception as e:
                logger.error(f"Failed to load FAISS index from {index_path}: {e}")
        return None
