"""LangChain embedding adapter powered by Sentence Transformers."""

from threading import RLock

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbeddings(Embeddings):
    """Generate local embeddings using a configured Sentence Transformers model."""

    def __init__(
        self,
        model_name: str,
        device: str,
        batch_size: int,
        normalize_embeddings: bool,
        show_progress: bool,
        local_files_only: bool,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._normalize_embeddings = normalize_embeddings
        self._show_progress = show_progress
        self._local_files_only = local_files_only
        self._model: SentenceTransformer | None = None
        self._model_lock = RLock()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document text in batches using the local model."""
        if not texts:
            return []

        with self._model_lock:
            vectors = self._get_model().encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=self._show_progress,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
            )
        return [vector.astype(float).tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        """Embed one similarity-search query."""
        return self.embed_documents([text])[0]

    def _get_model(self) -> SentenceTransformer:
        """Load the configured local model only when embeddings are first requested."""
        if self._model is None:
            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
                local_files_only=self._local_files_only,
                trust_remote_code=False,
            )
        return self._model
