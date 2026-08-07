"""Factory for wiring configured RAG adapters into the application pipeline."""

from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.cross_encoder_reranker import CrossEncoderReranker
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.hybrid_retriever import HybridRetriever
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)
from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult



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
    faiss_store = FAISSSimilarityStore(
        embeddings,
        settings.faiss_index_path,
        settings.faiss_allow_dangerous_deserialization,
        {
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )

    candidate_window = getattr(settings, "candidate_window", settings.reranker_top_n)
    final_top_k = getattr(settings, "final_top_k", settings.rag_search_limit)

    hybrid_retriever = HybridRetriever(
        similarity_store=faiss_store,
        bm25_top_k=candidate_window,
        dense_top_k=candidate_window,
        final_top_k=candidate_window,
        rrf_k=getattr(settings, "rrf_k", 60),
        weight_dense=getattr(settings, "weight_dense", 0.5),
        weight_sparse=getattr(settings, "weight_sparse", 0.5),
        fusion_mode=getattr(settings, "fusion_mode", "weighted_hybrid"),
        canonical_boost=getattr(settings, "rrf_canonical_boost", 0.060),
        duplicate_penalty=getattr(settings, "rrf_duplicate_penalty", 0.080),
    )

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
        device=settings.embedding_device,
        enabled=settings.reranker_enabled,
        top_n=candidate_window,
        top_m=final_top_k,
    )

    # Warm-up models
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Warming up Sentence Transformer and Cross Encoder models...")
        embeddings.embed_query("warmup")
        if settings.reranker_enabled:
            dummy_doc = KnowledgeDocument(content="warmup", metadata={"source": "warmup"})
            dummy_result = SearchResult(document=dummy_doc, distance=0.0)
            reranker.rerank("warmup", [dummy_result], top_m=1)
        logger.info("Models warmed up successfully.")
    except Exception as e:
        logger.warning(f"Failed to warm up models: {e}")

    if settings.faiss_index_path.exists() and (settings.faiss_index_path / "index.faiss").exists():
        try:
            hybrid_retriever.load()
        except Exception as e:
            import logging
            logging.warning(f"Could not load hybrid FAISS index from {settings.faiss_index_path}: {e}")

    return RAGPipeline(
        document_loader=KnowledgeLoader(
            settings.knowledge_source_path,
            settings.knowledge_max_file_size_bytes,
        ),
        document_chunker=SemanticDocumentChunker(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=settings.rag_chunk_separators,
            add_start_index=settings.rag_add_start_index,
        ),
        similarity_store=hybrid_retriever,
        search_limit=final_top_k,
        reranker=reranker,
        reranker_top_n=candidate_window,
        deduplicate_documents=getattr(settings, "deduplicate_documents", False),
    )
