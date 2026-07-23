"""CLI entrypoint for ingesting campus knowledge PDF documents into FAISS vector store."""

import logging

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

logger = logging.getLogger("campus_helpdesk.ingest")


def main() -> None:
    """Ingest all PDF files from knowledge_source_path into the FAISS index."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)

    source_dir = settings.knowledge_source_path
    if not source_dir.exists() or not source_dir.is_dir():
        logger.warning(f"Knowledge source directory does not exist or is not a directory: {source_dir}")
        return

    pdf_files = sorted(source_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info(f"No PDF files found in {source_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF file(s) in {source_dir} to ingest.")
    total_docs = 0
    total_chunks = 0

    for pdf_path in pdf_files:
        logger.info(f"Ingesting {pdf_path.name}...")
        try:
            # Pass persist=False during per-file ingestion to save only at the end
            result = pipeline.ingest_pdf(pdf_path, persist=False)
            total_docs += result.document_count
            total_chunks += result.chunk_count
            logger.info(f"Successfully ingested {pdf_path.name} ({result.document_count} pages, {result.chunk_count} chunks)")
        except Exception as err:
            logger.error(f"Failed to ingest {pdf_path.name}: {err}")

    if total_chunks > 0:
        pipeline._similarity_store.save()
        logger.info(f"Ingestion complete. Total documents: {total_docs}, total chunks: {total_chunks}. FAISS index saved.")
    else:
        logger.warning("No chunks were processed; FAISS index was not saved.")


if __name__ == "__main__":
    main()
