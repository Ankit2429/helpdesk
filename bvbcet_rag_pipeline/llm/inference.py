"""Local LLM Inference Engine.

Provides an injectable interface `LLMInferenceBackend` supporting Ollama,
llama.cpp, and Transformers without modifying other modules.
"""

from pathlib import Path
import time
from typing import Optional, Protocol, Tuple
import requests

from config.config import OLLAMA_API_URL, DEFAULT_MODEL
from logger.logger import get_logger

logger = get_logger("llm_inference")


class LLMInferenceBackend(Protocol):
    """Protocol for local LLM inference backends."""

    def generate(self, prompt: str) -> Tuple[Optional[str], float, Optional[str]]:
        """Generate LLM answer. Returns (answer_text, elapsed_seconds, error_detail)."""
        ...


class OllamaInferenceBackend:
    """Ollama REST API inference backend implementation."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_url: str = OLLAMA_API_URL,
        timeout: int = 60,
        temperature: float = 0.0,
    ) -> None:
        self.model_name = model_name
        self.api_url = api_url
        self.timeout = timeout
        self.temperature = temperature

    def generate(self, prompt: str) -> Tuple[Optional[str], float, Optional[str]]:
        """Call Ollama HTTP endpoint."""
        start_time = time.time()
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=self.timeout)
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip()
                if not answer:
                    return None, elapsed, "Ollama returned an empty response."
                logger.info(f"Ollama inference successful ({elapsed}s, Length: {len(answer)} chars)")
                return answer, elapsed, None
            else:
                error_msg = f"Ollama HTTP error {resp.status_code}: {resp.text.strip()}"
                logger.error(error_msg)
                return None, elapsed, error_msg
        except Exception as err:
            elapsed = round(time.time() - start_time, 2)
            error_msg = f"Error connecting to Ollama at {self.api_url}: {err}"
            logger.error(error_msg)
            return None, elapsed, error_msg


class LocalLLMInference:
    """Facade for local LLM inference backend."""

    def __init__(self, backend: Optional[LLMInferenceBackend] = None) -> None:
        self.backend = backend or OllamaInferenceBackend()

    def generate(self, prompt: str) -> Tuple[Optional[str], float, Optional[str]]:
        """Generate response via backend."""
        return self.backend.generate(prompt)
