"""Production Canonical FAISS Index Builder."""

import datetime
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import (
    SemanticDocumentChunker,
    compute_chunk_statistics,
)

logger = logging.getLogger(__name__)


class CanonicalIndexBuilder:
    """Builds a production FAISS vector index strictly from data/canonical_markdown/."""

    PIPELINE_VERSION = "1.0.0"

    def __init__(
        self,
        loader: KnowledgeLoader,
        chunker: SemanticDocumentChunker,
        similarity_store: FAISSSimilarityStore,
        canonical_dir: Path | str = "data/canonical_markdown",
    ) -> None:
        self.canonical_dir = Path(canonical_dir)
        self.loader = loader
        self.chunker = chunker
        self.similarity_store = similarity_store

    def build_index(self, force_rebuild: bool = False) -> dict[str, Any]:
        """Build or incrementally update FAISS vector index from canonical Markdown documents."""
        start_time = time.perf_counter()

        if not self.canonical_dir.exists():
            raise FileNotFoundError(f"Canonical Markdown directory does not exist: {self.canonical_dir}")

        md_files = list(self.canonical_dir.rglob("*.md"))
        if not md_files:
            raise ValueError(f"No canonical Markdown files (.md) found in {self.canonical_dir}")

        if force_rebuild:
            if hasattr(self.similarity_store, "reset"):
                self.similarity_store.reset()

        # Load existing manifest for incremental hash comparisons
        previous_hashes = self._load_previous_document_hashes() if not force_rebuild else {}

        current_hashes: dict[str, str] = {}
        all_chunks: list[KnowledgeDocument] = []
        failed_documents: list[dict[str, str]] = []

        documents_processed = 0
        duplicates_skipped = 0
        empty_skipped = 0

        for file_path in md_files:
            try:
                rel_path = file_path.relative_to(self.canonical_dir).as_posix()
                content = file_path.read_text(encoding="utf-8")
                if not content.strip():
                    empty_skipped += 1
                    logger.info("Skipping empty canonical document: %s", rel_path)
                    continue

                doc_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
                current_hashes[rel_path] = doc_hash

                if rel_path in previous_hashes and previous_hashes[rel_path] == doc_hash:
                    duplicates_skipped += 1
                    logger.debug("Skipping unchanged canonical document: %s", rel_path)
                    continue

                docs = self.loader.load(file_path)
                chunks = self.chunker.split(docs)

                all_chunks.extend(chunks)
                documents_processed += 1

            except Exception as err:
                logger.warning("Failed processing canonical document %s: %s", file_path, err)
                failed_documents.append({"file": str(file_path), "error": str(err)})

        if all_chunks:
            self.similarity_store.add(all_chunks)
            self.similarity_store.save()

        duration = round(time.perf_counter() - start_time, 3)
        chunk_stats = compute_chunk_statistics(all_chunks)

        build_stats = {
            "documents_processed": documents_processed,
            "chunks_created": chunk_stats["number_of_chunks"],
            "duplicates_skipped": duplicates_skipped,
            "empty_documents_skipped": empty_skipped,
            "average_chunks_per_document": (
                round(chunk_stats["number_of_chunks"] / documents_processed, 2)
                if documents_processed > 0
                else 0.0
            ),
            "processing_time_seconds": duration,
            "errors_count": len(failed_documents),
            "failed_documents": failed_documents,
        }

        # Write detailed manifest
        manifest = {
            "build_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pipeline_version": self.PIPELINE_VERSION,
            "embedding_model": str(self.similarity_store._embedding_metadata.get("embedding_model", "unknown")),
            "embedding_normalize": bool(self.similarity_store._embedding_metadata.get("embedding_normalize", True)),
            "embedding_dimension": 384,
            "faiss_index_type": "FAISS_FlatL2",
            "number_of_documents": documents_processed,
            "number_of_chunks": chunk_stats["number_of_chunks"],
            "average_chunk_size": chunk_stats["average_chunk_size"],
            "largest_chunk_size": chunk_stats["largest_chunk_size"],
            "smallest_chunk_size": chunk_stats["smallest_chunk_size"],
            "build_duration_seconds": duration,
            "document_hashes": current_hashes,
            "build_statistics": build_stats,
        }

        manifest_path = self.similarity_store._index_path / "index-manifest.json"
        self.similarity_store._index_path.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

        logger.info("Canonical Index Build complete: %s", build_stats)
        return build_stats

    def _load_previous_document_hashes(self) -> dict[str, str]:
        """Read document SHA256 hashes from existing index-manifest.json if present."""
        manifest_path = self.similarity_store._index_path / "index-manifest.json"
        if not manifest_path.is_file():
            return {}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data.get("document_hashes", {})
        except Exception:
            return {}
