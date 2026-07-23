"""ASGI application entry point."""

from fastapi import FastAPI

from campus_helpdesk.api.router import api_router
from campus_helpdesk.application.chat_service import DefaultChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import Settings, get_settings
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService


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
    app.state.chat_service = DefaultChatService(configured_llm_service)
    app.include_router(api_router)
    return app


app = create_app()
