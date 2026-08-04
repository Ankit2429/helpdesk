"""Production CLI script to build FAISS vector database from canonical Markdown knowledge."""

import logging
import time
from pathlib import Path

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.canonical_index_builder import CanonicalIndexBuilder
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")


def main() -> None:
    """Run production index builder from canonical Markdown data."""
    logger.info("Initializing production RAG ingestion pipeline...")
    settings = get_settings()

    pipeline = create_rag_pipeline(settings)
    builder = CanonicalIndexBuilder(
        loader=pipeline._document_loader,  # type: ignore[arg-type]
        chunker=pipeline._document_chunker,  # type: ignore[arg-type]
        similarity_store=pipeline._similarity_store,  # type: ignore[arg-type]
        canonical_dir=Path("data/canonical_markdown"),
    )

    logger.info("Building FAISS index from canonical source: %s", settings.knowledge_source_path)
    start_time = time.perf_counter()
    stats = builder.build_index(force_rebuild=True)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info("FAISS index build completed in %.2f ms", elapsed_ms)
    logger.info("PRODUCTION FAISS INDEX BUILD COMPLETE")
    logger.info("Source Directory: %s", settings.knowledge_source_path)
    logger.info("Documents Processed: %s", stats['documents_processed'])
    logger.info("Chunks Created: %s", stats['chunks_created'])
    logger.info("Avg Chunks/Doc: %s", stats['average_chunks_per_document'])
    logger.info("Build Time: %ss", stats['processing_time_seconds'])
    logger.info("FAISS Index Path: %s", settings.faiss_index_path)


if __name__ == "__main__":
    main()