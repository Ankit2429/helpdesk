"""Production CLI script to build FAISS vector database from canonical Markdown knowledge."""

import logging
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
        loader=pipeline._document_loader,
        chunker=pipeline._document_chunker,
        similarity_store=pipeline._similarity_store,
        canonical_dir=settings.knowledge_source_path,
    )

    logger.info("Building FAISS index from canonical source: %s", settings.knowledge_source_path)
    stats = builder.build_index(force_rebuild=True)

    print("\n=======================================================================")
    print("      PRODUCTION FAISS INDEX BUILD COMPLETE")
    print("=======================================================================")
    print(f"Source Directory    : {settings.knowledge_source_path}")
    print(f"Documents Processed : {stats['documents_processed']}")
    print(f"Chunks Created      : {stats['chunks_created']}")
    print(f"Avg Chunks/Doc      : {stats['average_chunks_per_document']}")
    print(f"Build Time          : {stats['processing_time_seconds']}s")
    print(f"FAISS Index Path    : {settings.faiss_index_path}")
    print("=======================================================================\n")


if __name__ == "__main__":
    main()