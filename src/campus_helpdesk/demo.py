"""MVP Standalone Laptop Demonstration Entrypoint."""

import logging
from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.pdf_loader import PDFKnowledgeLoader
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings
from campus_helpdesk.infrastructure.rag.text_chunker import RecursiveTextChunker
from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector
from campus_helpdesk.presentation.chat_window import ModernChatWindow

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the Offline Campus Helpdesk Robot Laptop Demonstration."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Initializing Campus Helpdesk Robot MVP Demo...")

    # 1. Initialize RAG dependencies
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=settings.embedding_show_progress,
        local_files_only=settings.embedding_local_files_only,
    )
    similarity_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=settings.faiss_index_path,
        allow_dangerous_deserialization=settings.faiss_allow_dangerous_deserialization,
        embedding_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )
    pdf_loader = PDFKnowledgeLoader(
        knowledge_source_path=settings.knowledge_source_path,
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )
    text_chunker = RecursiveTextChunker(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=settings.rag_chunk_separators,
        add_start_index=settings.rag_add_start_index,
    )

    rag_pipeline = RAGPipeline(
        document_loader=pdf_loader,
        document_chunker=text_chunker,
        similarity_store=similarity_store,
        search_limit=settings.rag_search_limit,
    )

    # Attempt to load pre-indexed vector store if present
    try:
        if settings.faiss_index_path.exists():
            rag_pipeline.load_index()
            logger.info("Loaded pre-existing FAISS vector store index.")
    except Exception as e:
        logger.warning(f"Could not load vector store index: {e}")

    # 2. Initialize LLM & Chat Services
    llm_service = OllamaLLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        generation_options=settings.ollama_options,
    )
    chat_service = RAGChatService(llm_service=llm_service, rag_pipeline=rag_pipeline)

    # 3. Initialize Vision & Audio Services
    detector = PersonDetector(
        webcam_index=settings.webcam_index,
        reset_frames_threshold=settings.person_detection_reset_frames,
    )
    stt_service = FasterWhisperSTTService(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    tts_service = NonBlockingTTSService(voice_model=settings.tts_voice_model)

    # 4. Launch Desktop GUI Window
    gui = ModernChatWindow(
        chat_service=chat_service,
        person_detector=detector,
        tts_service=tts_service,
        stt_service=stt_service,
        webcam_index=settings.webcam_index,
    )
    gui.start()


if __name__ == "__main__":
    main()
