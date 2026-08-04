"""Ollama-backed implementation of the language model boundary."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Protocol
from urllib.parse import urlparse

from campus_helpdesk.application.exceptions import ConfigurationError


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
    """Generate responses through a local Ollama model via services.llm_service.LLMService.

    Preserves signature compatibility while leveraging the core LLMService engine.
    """
    logger = logging.getLogger(__name__)

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
        self._generation_options = dict(generation_options)
        self._client = client
        temp = float(self._generation_options.get("temperature", 0.2))
        max_tok = int(self._generation_options.get("num_predict", 512))

        try:
            from campus_helpdesk.services.llm_service import LLMService as CoreLLMService
        except ImportError:
            from services.llm_service import LLMService as CoreLLMService
        self._core_service = CoreLLMService(
            model=model,
            host=base_url,
            temperature=temp,
            max_tokens=max_tok,
            timeout=timeout_seconds,
        )

    def generate(self, prompt: str) -> str:
        """Generate a complete response using the core LLMService or custom client."""
        if self._client is not None:
            opts = dict(self._generation_options)
            opts.setdefault("num_gpu", 0)
            res = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options=opts,
                stream=False,
            )
            msg = getattr(res, "message", res)
            content = getattr(msg, "content", str(msg))
            return content.strip()
        return self._core_service.generate(prompt)

    def generate_stream(self, prompt: str):
        """Generate a streaming response using the core LLMService or custom client."""
        if self._client is not None:
            opts = dict(self._generation_options)
            opts.setdefault("num_gpu", 0)
            res = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options=opts,
                stream=True,
            )
            if hasattr(res, "__iter__"):
                for chunk in res:
                    msg = getattr(chunk, "message", chunk)
                    yield getattr(msg, "content", str(msg))
            else:
                msg = getattr(res, "message", res)
                yield getattr(msg, "content", str(msg))
            return
        yield from self._core_service.generate_stream(prompt)

    @staticmethod
    def _validate_base_url(base_url: str) -> None:
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"}:
            raise ConfigurationError("Ollama base URL must use http or https scheme.")

