"""FAISS-backed local similarity store using LangChain's vector-store adapter."""

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from threading import RLock

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from campus_helpdesk.application.exceptions import RetrievalError
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult

logger = logging.getLogger(__name__)

_MANIFEST_FILENAME = "index-manifest.json"


class FAISSSimilarityStore:
    """Maintain and persist a local FAISS index for knowledge chunks."""

    def __init__(
        self,
        embeddings: Embeddings,
        index_path: Path,
        allow_dangerous_deserialization: bool,
        embedding_metadata: dict[str, str | bool],
    ) -> None:
        self._embeddings = embeddings
        self._index_path = index_path
        self._allow_dangerous_deserialization = allow_dangerous_deserialization
        self._embedding_metadata = dict(embedding_metadata)
        self._store: FAISS | None = None
        self._store_lock = RLock()

    def reset(self) -> None:
        """Reset in-memory FAISS store state."""
        with self._store_lock:
            self._store = None

    def add(self, documents: Sequence[KnowledgeDocument]) -> None:
        """Embed and add documents, creating the local index on first use."""
        with self._store_lock:
            if not documents:
                return

            langchain_documents = [
                Document(page_content=document.content, metadata=dict(document.metadata)) for document in documents
            ]
            if self._store is None:
                self._store = FAISS.from_documents(langchain_documents, self._embeddings)
            else:
                self._store.add_documents(langchain_documents)

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return indexed chunks ordered by FAISS distance score."""
        with self._store_lock:
            if self._store is None:
                logger.error("Retrieval failed: FAISS index not loaded.")
                raise RetrievalError("FAISS index not loaded; cannot perform retrieval.")

            matches = self._store.similarity_search_with_score(query, k=limit)
            return [
                SearchResult(
                    document=KnowledgeDocument(
                        content=document.page_content,
                        metadata={str(key): str(value) for key, value in document.metadata.items()},
                    ),
                    distance=float(distance),
                )
                for document, distance in matches
            ]

    def save(self) -> None:
        """Persist the index locally for later process restarts."""
        with self._store_lock:
            if self._store is None:
                raise RuntimeError("Cannot persist an empty FAISS index.")

            self._index_path.mkdir(parents=True, exist_ok=True)
            self._store.save_local(str(self._index_path))
            self._write_manifest()
            logger.info("FAISS index persisted", extra={"index_path": str(self._index_path)})

    def load(self) -> None:
        """Load a locally generated FAISS index from the configured directory."""
        if not self._allow_dangerous_deserialization:
            raise PermissionError(
                "FAISS loading is disabled until trusted-index deserialization is explicitly enabled."
            )

        with self._store_lock:
            if not self._index_path.is_dir():
                logger.error("Retrieval failed: FAISS index directory missing.")
                raise RetrievalError("Missing FAISS index directory.")
            try:
                self._validate_manifest()
            except (ValueError, json.JSONDecodeError) as err:
                logger.error("Retrieval failed: corrupted FAISS index manifest: %s", err)
                raise RetrievalError("Corrupted FAISS index manifest.")
            try:
                self._store = FAISS.load_local(
                    str(self._index_path),
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                logger.info("FAISS index loaded", extra={"index_path": str(self._index_path)})
            except Exception as err:
                logger.error("Retrieval failed: error loading FAISS index: %s", err)
                raise RetrievalError("Failed to load FAISS index.")

    def _write_manifest(self) -> None:
        """Record the embedding settings required to interpret this index."""
        manifest_path = self._index_path / _MANIFEST_FILENAME
        manifest_path.write_text(json.dumps(self._embedding_metadata, sort_keys=True), encoding="utf-8")

    def _validate_manifest(self) -> None:
        """Reject an index built with a different embedding configuration."""
        manifest_path = self._index_path / _MANIFEST_FILENAME
        try:
            index_metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ValueError("FAISS index metadata is missing. Rebuild the index before loading it.") from error
        except json.JSONDecodeError as error:
            raise ValueError("FAISS index metadata is invalid. Rebuild the index before loading it.") from error

        for key, expected_value in self._embedding_metadata.items():
            if index_metadata.get(key) != expected_value:
                raise ValueError(
                    f"FAISS index embedding configuration differs for '{key}'. "
                    f"Expected '{expected_value}', got '{index_metadata.get(key)}'. Rebuild the index before loading it."
                )
