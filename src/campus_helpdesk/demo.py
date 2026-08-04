"""MVP Standalone Laptop Demonstration Entrypoint."""

import logging
import os
from pathlib import Path

import ollama

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)
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
    markdown_loader = MarkdownKnowledgeLoader(
        knowledge_source_path=settings.knowledge_source_path,
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )
    text_chunker = SemanticDocumentChunker(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=settings.rag_chunk_separators,
        add_start_index=settings.rag_add_start_index,
    )

    rag_pipeline = RAGPipeline(
        document_loader=markdown_loader,
        document_chunker=text_chunker,
        similarity_store=similarity_store,
        search_limit=settings.rag_search_limit,
    )

    # Attempt to load pre-indexed vector store if present
    index_loaded = False
    try:
        if settings.faiss_index_path.exists():
            rag_pipeline.load_index()
            index_loaded = True
            logger.info("Loaded pre-existing FAISS vector store index.")
    except Exception as e:
        logger.warning(f"Could not load vector store index: {e}")

    if not index_loaded:
        logger.info("Ingesting knowledge source directory...")
        for root, _, files in os.walk(settings.knowledge_source_path):
            for file in files:
                if file.endswith((".md", ".pdf")):
                    file_path = Path(root) / file
                    try:
                        rag_pipeline.ingest_file(file_path, persist=False)
                        logger.info(f"Ingested file: {file_path.name}")
                    except Exception as exc:
                        logger.warning(f"Failed to ingest {file_path}: {exc}")
        rag_pipeline._similarity_store.save()
        logger.info("Saved vector store index.")

    # 2. Initialize LLM & Chat Services
    ollama_host = settings.ollama_base_url
    client = ollama.Client(host=ollama_host, timeout=settings.ollama_timeout_seconds)
    from campus_helpdesk.infrastructure.llm.factory import create_llm_service
    llm_service = create_llm_service(settings)

    logger.info("OLLAMA_HOST: %s", ollama_host)
    logger.info("OLLAMA_MODEL: %s", settings.ollama_model)
    # Verify Ollama connection with client.list()
    try:
        client.list()
        logger.info("Ollama connection verified.")
    except Exception as exc:
        logger.error(f"client.list() failed: {exc}")
        raise
    # Test client.chat(...) with exact client object used by application
    try:
        client.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            options={"num_gpu": 0},
        )
    except Exception as exc:
        exc_type = type(exc).__name__
        http_status = getattr(exc, "status_code", getattr(getattr(exc, "response", None), "status_code", None))
        response_body = getattr(exc, "text", getattr(getattr(exc, "response", None), "text", getattr(exc, "error", str(exc))))
        req_obj = getattr(exc, "request", None)
        request_url = getattr(getattr(req_obj, "url", None), "__str__", lambda: None)() if req_obj else getattr(exc, "url", None)
        logger.error(
            f"Ollama chat failed:\n"
            f"  Exception type: {exc_type}\n"
            f"  HTTP status: {http_status}\n"
            f"  Response body: {response_body}\n"
            f"  Request URL: {request_url}"
        )
        raise
    # Verify by asking: "What is your name?" before launching the GUI
    name_response = llm_service.generate("What is your name?")
    logger.info(f"Ollama verification response: {name_response}")

    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
    )

    # 3. Initialize Vision & Audio Services
    detector = PersonDetector(
        webcam_index=settings.webcam_index,
        reset_frames_threshold=settings.person_detection_reset_frames,
    )
    stt_service = FasterWhisperSTTService(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        device_index=settings.stt_device_index,
        enable_online_fallback=settings.stt_enable_online_fallback,
        debug=settings.debug,
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
