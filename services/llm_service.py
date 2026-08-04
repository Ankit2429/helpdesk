"""
services/llm_service.py

Production-Ready Ollama LLM Service for Helpdesk Robot.
Interfaces with local Ollama service using the official Python client.

Provides clean OOP design with timeout handling, exponential backoff retries,
model availability detection, and comprehensive logging.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Iterator, Optional, Tuple

from ollama import Client, RequestError, ResponseError

logger = logging.getLogger("services.llm_service")


class LLMService:
    """
    Modular LLM service wrapping official Ollama Python SDK.

    Attributes:
        model: Model identifier tag (default: 'llama3.2:3b').
        host: Base URL for Ollama service (default: 'http://localhost:11434').
        temperature: Generation sampling temperature.
        max_tokens: Maximum response tokens to generate.
        timeout: Network timeout in seconds for API calls.
        max_retries: Number of retry attempts on transient network failures.
        backoff_factor: Multiplier for exponential backoff delay.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
        max_tokens: int = 512,
        timeout: float = 180.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> None:
        """
        Initialize LLMService instance.

        Args:
            model: Ollama model name/tag (e.g. 'llama3.2:3b').
            host: Host URL of running Ollama server.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum prediction tokens.
            timeout: Request timeout in seconds.
            max_retries: Retry count for transient errors.
            backoff_factor: Backoff multiplier between retries.
        """
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._client: Optional[Client] = None
        self._response_cache: Dict[str, str] = {}
        self._cache_max_size: int = 200
        self._init_client()

    def _init_client(self) -> None:
        """Construct the official Ollama Python Client."""
        try:
            self._client = Client(host=self.host, timeout=self.timeout)
            logger.info(f"[Ollama Init] Client connected at host '{self.host}' for model '{self.model}'.")
        except Exception as err:
            logger.error(f"[Ollama Init Error] Failed to initialize Ollama Client: {err}")
            self._client = None

    def check_connection(self) -> Tuple[bool, str]:
        """
        Check if Ollama server is reachable and target model is pulled.

        Returns:
            Tuple of (is_available: bool, status_message: str)
        """
        try:
            if not self._client:
                self._init_client()
            if not self._client:
                return False, f"Could not initialize Ollama client at {self.host}."

            models_response = self._client.list()
            raw_models = getattr(models_response, "models", []) or []
            if isinstance(models_response, dict):
                raw_models = models_response.get("models", [])

            model_names = []
            for m in raw_models:
                name = getattr(m, "model", None) or getattr(m, "name", None)
                if isinstance(m, dict):
                    name = m.get("model") or m.get("name")
                if name:
                    model_names.append(name)

            target = self.model.lower()
            base_target = target.split(":")[0]

            has_model = any(
                m.lower() == target or m.lower().startswith(base_target)
                for m in model_names
            )

            if not has_model:
                msg = (
                    f"Ollama is running at {self.host}, but model '{self.model}' is not pulled.\n"
                    f"Please run: & \"$env:LOCALAPPDATA\\Programs\\Ollama\\ollama.exe\" pull {self.model} (or 'ollama pull {self.model}')"
                )
                logger.warning(msg)
                return False, msg

            success_msg = f"Ollama is connected at {self.host}. Model '{self.model}' is ready."
            logger.info(success_msg)
            return True, success_msg

        except Exception as exc:
            err_msg = (
                f"Ollama service is unavailable on {self.host}.\n"
                f"Please ensure Ollama is running.\n"
                f"Details: {exc}"
            )
            logger.error(err_msg)
            return False, err_msg

    def generate(self, prompt: str) -> str:
        """
        Send user/system prompt to Ollama and return generated response text.

        Includes query response caching, logging, timeout handling, and retry logic.

        Args:
            prompt: Text prompt sent to LLM.

        Returns:
            Generated response string from Ollama.
        """
        cache_key = prompt.strip()
        if cache_key in self._response_cache:
            logger.info(f"[LLM Cache Hit] Returning cached response for prompt length={len(prompt)} chars")
            return self._response_cache[cache_key]

        logger.info(f"[Ollama Started] Model='{self.model}', Prompt Length={len(prompt)} chars")
        if "Context:" in prompt:
            logger.info("[Retrieval Completed] Retrieved RAG context included in LLM prompt.")

        if not self._client:
            self._init_client()

        options: Dict[str, Any] = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "keep_alive": "10m",
        }

        last_exception: Optional[Exception] = None
        delay = 0.3
        start_time = time.time()

        for attempt in range(1, self.max_retries + 1):
            try:
                if not self._client:
                    raise RequestError(f"Ollama client not initialized for host {self.host}")

                response = self._client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    options=options,
                    stream=False,
                )

                content = ""
                if hasattr(response, "message") and hasattr(response.message, "content"):
                    content = response.message.content
                elif isinstance(response, dict):
                    content = response.get("message", {}).get("content", "")

                content = content.strip()
                if not content:
                    raise ResponseError("Ollama returned an empty response.")

                elapsed = (time.time() - start_time) * 1000
                logger.info(f"[Response Finished] Generation complete in {elapsed:.1f}ms (Length={len(content)} chars)")
                
                # Update query cache
                if len(self._response_cache) >= self._cache_max_size:
                    self._response_cache.clear()
                self._response_cache[cache_key] = content
                return content

            except (ResponseError, RequestError, Exception) as exc:
                last_exception = exc
                logger.warning(f"[LLM Retry {attempt}/{self.max_retries}] Failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.backoff_factor

        error_details = (
            f"Ollama service is unavailable or model '{self.model}' failed to respond.\n"
            f"Please verify Ollama is running at {self.host}.\n"
            f"If the model is missing, run: ollama pull {self.model}\n"
            f"Error details: {last_exception}"
        )
        logger.error(f"[LLM Execution Failed] {error_details}")
        return f"[Helpdesk Offline Service Warning] {error_details}"

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """
        Yield generated tokens incrementally for low-latency streaming UI responses.

        Args:
            prompt: Text prompt sent to LLM.

        Yields:
            Token chunks as strings.
        """
        logger.info(f"[Ollama Started] Model='{self.model}', Streaming mode initialized")
        if not self._client:
            self._init_client()

        options: Dict[str, Any] = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "keep_alive": "10m",
        }

        start_time = time.time()
        first_token_logged = False
        total_tokens = 0

        try:
            if not self._client:
                raise RequestError(f"Ollama client not initialized for host {self.host}")

            response = self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options=options,
                stream=True,
            )

            for chunk in response:
                token = ""
                if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    token = chunk.message.content
                elif isinstance(chunk, dict):
                    token = chunk.get("message", {}).get("content", "")
                if token:
                    if not first_token_logged:
                        first_token_time = (time.time() - start_time) * 1000
                        logger.info(f"[First Token Received] Latency: {first_token_time:.1f}ms")
                        first_token_logged = True
                    total_tokens += 1
                    yield token

            total_time = (time.time() - start_time) * 1000
            logger.info(f"[Response Finished] Streamed {total_tokens} tokens in {total_time:.1f}ms")

        except Exception as exc:
            logger.error(f"[Ollama Streaming Error] {exc}")
            yield f"[Ollama Error: {exc}]"
