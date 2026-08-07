"""Factory for constructing configured LLM services and GenerationRouters."""

import logging

from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.llm.cloud_llm_service import CloudLLMService
from campus_helpdesk.infrastructure.llm.connectivity_checker import ConnectivityChecker
from campus_helpdesk.infrastructure.llm.generation_router import GenerationRouter
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService

logger = logging.getLogger(__name__)


def create_llm_service(settings: Settings) -> LLMService:
    """Construct an LLMService (GenerationRouter wrapping local Ollama and optional Cloud Gemini).

    Args:
        settings: Application Settings instance.

    Returns:
        Configured LLMService protocol implementation.
    """
    # Local offline model uses settings.offline_llm_model or settings.ollama_model
    offline_model = getattr(settings, "offline_llm_model", settings.ollama_model)
    local_llm = OllamaLLMService(
        base_url=settings.ollama_base_url,
        model=offline_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        generation_options=settings.ollama_options,
    )

    # Warm-up Ollama
    try:
        logger.info("Warming up Ollama LLM model...")
        # Since options are passed at init, we just send a very short prompt to load the model into VRAM
        list(local_llm.generate_stream("hi"))
        logger.info("Ollama LLM model warmed up successfully.")
    except Exception as e:
        logger.warning(f"Failed to warm up Ollama LLM model: {e}")

    cloud_llm = None
    if settings.cloud_llm_api_key.strip():
        try:
            cloud_llm = CloudLLMService(settings=settings)
        except Exception as e:
            logger.warning(f"Could not initialize CloudLLMService: {e}")

    checker = ConnectivityChecker(settings=settings)

    return GenerationRouter(
        local_llm_service=local_llm,
        cloud_llm_service=cloud_llm,
        connectivity_checker=checker,
        enable_router=settings.enable_cloud_llm_router,
        settings=settings,
    )
