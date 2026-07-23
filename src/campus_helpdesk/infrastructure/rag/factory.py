"""Factory for wiring configured RAG adapters into the application pipeline."""

from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.pdf_loader import PDFKnowledgeLoader
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings
from campus_helpdesk.infrastructure.rag.text_chunker import RecursiveTextChunker


def create_rag_pipeline(settings: Settings) -> RAGPipeline:
    """Build a locally configured RAG pipeline without starting ingestion."""
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=settings.embedding_show_progress,
        local_files_only=settings.embedding_local_files_only,
    )
    return RAGPipeline(
        document_loader=PDFKnowledgeLoader(
            settings.knowledge_source_path,
            settings.knowledge_max_file_size_bytes,
        ),
        document_chunker=RecursiveTextChunker(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=settings.rag_chunk_separators,
            add_start_index=settings.rag_add_start_index,
        ),
        similarity_store=FAISSSimilarityStore(
            embeddings,
            settings.faiss_index_path,
            settings.faiss_allow_dangerous_deserialization,
            {
                "embedding_model": settings.embedding_model,
                "embedding_normalize": settings.embedding_normalize,
            },
        ),
        search_limit=settings.rag_search_limit,
    )
