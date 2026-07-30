"""LangChain embedding adapter powered by Sentence Transformers."""

from functools import lru_cache
from threading import RLock
from typing import List

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
        # Use the unified encode method which handles caching and batch processing.
        return self.encode(texts)

    # Legacy cached method retained for compatibility but not used in the new implementation.
    @lru_cache(maxsize=128)
    def _cached_encode(self, text: str) -> List[float]:
        """Internal cached encode for a single text string (fallback)."""
        if self._model is None:
            self._model = self._get_model()
        return self._model.encode([text], normalize_embeddings=self._normalize_embeddings)[0].astype(float).tolist()

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of strings into embeddings with manual caching.

        This implementation caches individual text embeddings in an internal
        dictionary ``self._cache``. Uncached texts are encoded in a single batch
        to minimise model calls, then stored in the cache for future reuse.
        """
        # Ensure the cache dict exists
        if not hasattr(self, "_cache"):
            self._cache = {}
        results: List[List[float]] = []
        uncached_texts: List[str] = []
        uncached_indices: List[int] = []
        for idx, txt in enumerate(texts):
            if txt in self._cache:
                results.append(self._cache[txt])
            else:
                # placeholder, will fill later
                results.append([])  # type: ignore
                uncached_texts.append(txt)
                uncached_indices.append(idx)
        # Batch encode any uncached texts
        if uncached_texts:
            model = self._get_model()
            batch_embeddings = model.encode(
                uncached_texts,
                batch_size=self._batch_size,
                show_progress_bar=self._show_progress,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
            )
            for i, emb in enumerate(batch_embeddings):
                emb_list = emb.astype(float).tolist()
                txt = uncached_texts[i]
                self._cache[txt] = emb_list
                results[uncached_indices[i]] = emb_list
        return results

    def embed_query(self, text: str) -> list[float]:
        """Embed one similarity-search query."""
        return self.embed_documents([text])[0]

    def embed_text(self, text: str) -> list[float]:
        """Embed a single piece of text (compatibility alias for embed_query)."""
        return self.embed_query(text)

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
