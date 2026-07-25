"""Ollama-backed implementation of the language model boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from urllib.parse import urlparse

from ollama import Client

from campus_helpdesk.application.exceptions import LLMServiceError


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
    """Generate responses through a local Ollama model."""

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
        try:
            response = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options=self._generation_options,
                stream=False,
            )
            content = response.message.content.strip()
        except Exception as error:
            raise LLMServiceError(f"{type(error).__name__}: {error}") from error

        if not content:
            raise LLMServiceError("Ollama returned an empty response.")

        return content

    def generate_stream(self, prompt: str):
        """Generate a response using the configured local model, yielding chunks as they arrive."""
        try:
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
        except Exception as error:
            raise LLMServiceError(f"{type(error).__name__}: {error}") from error

    @staticmethod
    def _validate_base_url(base_url: str) -> None:
        """Ensure adapter construction cannot send prompts to a remote Ollama host."""
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or parsed_url.hostname not in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            raise ValueError("Ollama base URL must use a loopback host for offline operation.")
