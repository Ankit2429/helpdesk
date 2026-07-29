"""ASGI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from campus_helpdesk.api.router import api_router
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.rag_chat_service import RAGChatService, DEFAULT_SYSTEM_PROMPT
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import Settings, get_settings
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

# Dependency imports for explicit wiring
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, llm_service: LLMService | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    application_settings = settings or get_settings()
    configure_logging(application_settings.log_level)

    app = FastAPI(
        title=application_settings.app_name,
        version=application_settings.app_version,
        debug=application_settings.debug,
    )
    # Enable CORS (adjust origins as needed for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = application_settings
    configured_llm_service = llm_service or OllamaLLMService(
        base_url=application_settings.ollama_base_url,
        model=application_settings.ollama_model,
        timeout_seconds=application_settings.ollama_timeout_seconds,
        generation_options=application_settings.ollama_options,
    )
    rag_pipeline = create_rag_pipeline(application_settings)
    if application_settings.faiss_index_path.exists():
        try:
            rag_pipeline.load_index()
        except Exception as exc:
            logger.warning(
                "Could not load FAISS index from %s: %s",
                application_settings.faiss_index_path,
                exc,
            )

    # Explicitly instantiate dependencies for RAGChatService
    session_mgr = SessionManager()
    query_rw = QueryRewriter()
    confidence_eng = ConfidenceEngine()
    answerability_eng = AnswerabilityEngine()
    context_builder = PromptContextBuilder(
        max_context_size=3000,
        similarity_threshold=application_settings.rag_distance_threshold,
    )

    app.state.chat_service = RAGChatService(
        llm_service=configured_llm_service,
        rag_pipeline=rag_pipeline,
        query_rewriter=query_rw,
        context_builder=context_builder,
        session_manager=session_mgr,
        confidence_engine=confidence_eng,
        answerability_engine=answerability_eng,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )

    app.include_router(api_router)
    return app


app = create_app()
