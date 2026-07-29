"""Ollama-backed implementation of the language model boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from urllib.parse import urlparse

from ollama import Client

from campus_helpdesk.application.exceptions import LLMServiceError, ConfigurationError
import logging
import time


class OllamaClient(Protocol):
    """Subset of the Ollama client used by this adapter."""

    def list(self) -> object:
        """List available local models."""

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        options: Mapping[str, float | int] | None = None,
        stream: bool = False,
    ) -> OllamaChatResponse:
        """Send a non-streaming chat request to Ollama."""


class OllamaMessage(Protocol):
    """Message subset returned by the Ollama client."""

    content: str


class OllamaChatResponse(Protocol):
    """Response subset returned by the Ollama client."""

    message: OllamaMessage


class OllamaLLMService:
    """Generate responses through a local Ollama model.

    All public methods preserve the original signature, but now include retry
    handling for transient network failures.
    """
    # Retry configuration (could be exposed via Settings in future)
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 0.2  # seconds
    BACKOFF_FACTOR = 2.0

    logger = logging.getLogger(__name__)

    def _retry_operation(self, func, *args, **kwargs):
        """Execute *func* with retry logic for transient failures.

        Retries are performed for generic exceptions raised by the Ollama client.
        Configuration errors are raised immediately without retry.
        """
        backoff = self.INITIAL_BACKOFF
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except ConfigurationError:
                self.logger.error("Configuration error during Ollama request: %s", func.__name__)
                raise
            except Exception as exc:  # pylint: disable=broad-except
                if attempt == self.MAX_RETRIES:
                    self.logger.error("Ollama %s failed after %d attempts: %s", func.__name__, attempt, exc)
                    raise LLMServiceError(f"{type(exc).__name__}: {exc}") from exc
                else:
                    self.logger.debug("Retry %d/%d for Ollama %s after error: %s", attempt, self.MAX_RETRIES, func.__name__, exc)
                    time.sleep(backoff)
                    backoff *= self.BACKOFF_FACTOR
        raise LLMServiceError("Unexpected retry exhaustion")

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        generation_options: Mapping[str, float | int],
        client: OllamaClient | None = None,
    ) -> None:
        self._validate_base_url(base_url)
        self._model = model
        options = dict(generation_options)
        options.setdefault("num_predict", 50)
        options.setdefault("temperature", 0.1)
        self._generation_options = options
        self._client = client or Client(host=base_url, timeout=timeout_seconds)

    def generate(self, prompt: str) -> str:
        """Generate a complete response using the configured local model."""
        def _call():
            response = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options=self._generation_options,
                stream=False,
            )
            content = response.message.content.strip()
            if not content:
                raise LLMServiceError("Ollama returned an empty response.")
            return content

        return self._retry_operation(_call)

    def generate_stream(self, prompt: str):
        """Generate a response using the configured local model, yielding chunks as they arrive."""
        def _call():
            response = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options=self._generation_options,
                stream=True,
            )
            for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        return self._retry_operation(_call)

    @staticmethod
    def _validate_base_url(base_url: str) -> None:
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"}:
            raise ConfigurationError("Ollama base URL must use http or https scheme.")
