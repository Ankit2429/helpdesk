"""ASGI application entry point."""

from fastapi import FastAPI

from campus_helpdesk.api.router import api_router
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import Settings, get_settings
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline


def create_app(settings: Settings | None = None, llm_service: LLMService | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    application_settings = settings or get_settings()
    configure_logging(application_settings.log_level)

    app = FastAPI(
        title=application_settings.app_name,
        version=application_settings.app_version,
        debug=application_settings.debug,
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
        except Exception:
            pass
    app.state.chat_service = RAGChatService(configured_llm_service, rag_pipeline=rag_pipeline)
    app.include_router(api_router)
    return app


app = create_app()
