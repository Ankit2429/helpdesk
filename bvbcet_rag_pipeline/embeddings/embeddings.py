"""Embedding Manager module to load HuggingFace sentence transformer embeddings."""

from langchain_community.embeddings import HuggingFaceEmbeddings


class EmbeddingManager:
    """Manager for loading embedding model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """Get initialized embedding instance."""
        return self.embeddings
