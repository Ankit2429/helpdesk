"""Generation router for dynamic selection between Cloud LLM and Local LLM."""

import logging
from typing import Optional

from campus_helpdesk.application.exceptions import CloudLLMServiceError, LLMServiceError
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.llm.connectivity_checker import ConnectivityChecker

logger = logging.getLogger(__name__)


class GenerationRouter(LLMService):
    """Routes generation requests dynamically to Cloud LLM or Local LLM based on connectivity, settings, and health."""

    def __init__(
        self,
        local_llm_service: LLMService,
        cloud_llm_service: Optional[LLMService] = None,
        connectivity_checker: Optional[ConnectivityChecker] = None,
        enable_router: bool = False,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the GenerationRouter.

        Args:
            local_llm_service: Required fallback/offline local LLM service (e.g. OllamaLLMService).
            cloud_llm_service: Optional cloud LLM service (e.g. CloudLLMService for Gemini).
            connectivity_checker: Optional connectivity checker helper.
            enable_router: Feature flag to enable cloud routing. If False, operates as direct local passthrough.
            settings: Application settings instance.
        """
        self.local_llm_service = local_llm_service
        self.cloud_llm_service = cloud_llm_service

        if settings is not None:
            self.enable_router = settings.enable_cloud_llm_router
            self.connectivity_checker = connectivity_checker or ConnectivityChecker(settings=settings)
        else:
            self.enable_router = enable_router
            self.connectivity_checker = connectivity_checker or (ConnectivityChecker() if enable_router else None)

        self.last_used_backend: str = "UNINITIALIZED"

    def generate(self, prompt: str) -> str:
        """Generate text prompt response by routing to Cloud LLM when online or Local LLM when offline/fallback.

        Args:
            prompt: Text prompt string.

        Returns:
            Generated response string.
        """
        # If router is disabled or cloud service is missing, route directly to local LLM with zero overhead
        if not self.enable_router or self.cloud_llm_service is None:
            self.last_used_backend = "LOCAL (Router Disabled / Cloud Unconfigured)"
            logger.info(f"GenerationRouter -> {self.last_used_backend}")
            return self.local_llm_service.generate(prompt)

        # Check online connectivity
        checker = self.connectivity_checker or ConnectivityChecker()
        is_online = checker.is_online()

        if is_online:
            try:
                logger.info("Online connectivity detected. Attempting Cloud LLM generation...")
                res = self.cloud_llm_service.generate(prompt)
                provider = getattr(self.cloud_llm_service, "provider", "cloud").upper()
                model = getattr(self.cloud_llm_service, "model", "")
                model_str = f" - {model}" if model else ""
                self.last_used_backend = f"CLOUD ({provider}{model_str})"
                logger.info(f"GenerationRouter -> {self.last_used_backend}")
                return res
            except Exception as err:
                self.last_used_backend = f"LOCAL (FALLBACK: Cloud API error -> {type(err).__name__}: {err})"
                logger.warning(
                    f"Cloud LLM generation failed ({type(err).__name__}: {err}). "
                    f"Falling back to local LLM service. Backend: {self.last_used_backend}"
                )
                return self.local_llm_service.generate(prompt)

        self.last_used_backend = "LOCAL (Offline Detected)"
        logger.info(f"GenerationRouter -> {self.last_used_backend}")
        return self.local_llm_service.generate(prompt)

    def generate_stream(self, prompt: str):
        """Yield response tokens incrementally by routing to Cloud LLM or Local LLM.

        Args:
            prompt: Text prompt string.

        Yields:
            Response tokens as strings.
        """
        # If router is disabled or cloud service is missing, route directly to local LLM with zero overhead
        if not self.enable_router or self.cloud_llm_service is None:
            self.last_used_backend = "LOCAL (Router Disabled / Cloud Unconfigured)"
            logger.info(f"GenerationRouter (stream) -> {self.last_used_backend}")
            yield from self.local_llm_service.generate_stream(prompt)
            return

        # Check online connectivity
        checker = self.connectivity_checker or ConnectivityChecker()
        is_online = checker.is_online()

        if is_online:
            try:
                provider = getattr(self.cloud_llm_service, "provider", "cloud").upper()
                model = getattr(self.cloud_llm_service, "model", "")
                model_str = f" - {model}" if model else ""
                self.last_used_backend = f"CLOUD ({provider}{model_str} Stream)"
                yield from self.cloud_llm_service.generate_stream(prompt)
                return
            except Exception as err:
                self.last_used_backend = f"LOCAL (FALLBACK: Cloud API stream error -> {type(err).__name__}: {err})"
                logger.warning(
                    f"Cloud LLM stream generation failed ({type(err).__name__}: {err}). "
                    f"Falling back to local LLM streaming. Backend: {self.last_used_backend}"
                )
                yield from self.local_llm_service.generate_stream(prompt)
                return

        self.last_used_backend = "LOCAL (Offline Detected)"
        logger.info(f"GenerationRouter (stream) -> {self.last_used_backend}")
        yield from self.local_llm_service.generate_stream(prompt)
