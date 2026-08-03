"""Cloud LLM service implementation for Gemini API."""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from campus_helpdesk.application.exceptions import CloudLLMServiceError
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.config.settings import Settings

logger = logging.getLogger(__name__)


class CloudLLMService(LLMService):
    """Generates text responses from cloud-hosted Gemini LLM endpoint via REST API."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-1.5-flash",
        provider: str = "gemini",
        timeout_seconds: float = 10.0,
        settings: Optional[Settings] = None,
    ) -> None:
        if settings is not None:
            self.api_key = settings.cloud_llm_api_key.strip()
            self.model = settings.cloud_llm_model.strip() or "gemini-1.5-flash"
            self.provider = settings.cloud_llm_provider.strip().lower() or "gemini"
            self.timeout_seconds = settings.cloud_llm_timeout_seconds
        else:
            self.api_key = api_key.strip()
            self.model = model.strip() or "gemini-1.5-flash"
            self.provider = provider.strip().lower() or "gemini"
            self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        """Generate text from the configured cloud LLM API.

        Args:
            prompt: Text prompt sent to cloud model.

        Returns:
            Generated text string response.

        Raises:
            CloudLLMServiceError: If API key is missing, network times out, or API returns error.
        """
        if not self.api_key:
            raise CloudLLMServiceError("Cloud LLM API key is not configured.")

        if self.provider in ("openrouter", "openai"):
            return self._generate_openrouter(prompt)
        elif self.provider == "gemini":
            return self._generate_gemini(prompt)
        else:
            raise CloudLLMServiceError(f"Unsupported cloud LLM provider: {self.provider}")

    def generate_stream(self, prompt: str):
        """Yield tokens incrementally from the configured cloud LLM API.

        Args:
            prompt: Text prompt sent to cloud model.

        Yields:
            Token chunks as strings.

        Raises:
            CloudLLMServiceError: If API key is missing or connection fails.
        """
        if not self.api_key:
            raise CloudLLMServiceError("Cloud LLM API key is not configured.")

        if self.provider in ("openrouter", "openai"):
            yield from self._generate_stream_openrouter(prompt)
        elif self.provider == "gemini":
            yield from self._generate_stream_gemini(prompt)
        else:
            raise CloudLLMServiceError(f"Unsupported cloud LLM provider: {self.provider}")

    def _generate_gemini(self, prompt: str) -> str:
        """Call Google Gemini generateContent REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                return self._extract_gemini_text(res_json)
        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                error_body = err.read().decode("utf-8")
            except Exception:
                pass
            msg = f"Gemini API returned status {err.code}: {err.reason}. {error_body}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except urllib.error.URLError as err:
            msg = f"Gemini API connection failed: {err.reason}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except TimeoutError as err:
            msg = f"Gemini API request timed out after {self.timeout_seconds}s"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except json.JSONDecodeError as err:
            msg = f"Failed to parse Gemini API JSON response: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except Exception as err:
            msg = f"Unexpected cloud LLM error: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err

    def _extract_gemini_text(self, res_json: dict) -> str:
        """Extract response text string from Gemini API response structure."""
        try:
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise CloudLLMServiceError("Gemini API response contained no candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise CloudLLMServiceError("Gemini API candidate response contained no text parts.")

            text = parts[0].get("text", "").strip()
            if not text:
                raise CloudLLMServiceError("Gemini API candidate response returned empty text.")

            return text
        except (KeyError, IndexError, TypeError) as err:
            raise CloudLLMServiceError(f"Malformed Gemini API response payload: {err}") from err

    def _generate_openrouter(self, prompt: str) -> str:
        """Call OpenRouter OpenAI-compatible chat completion REST API."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/Ankit2429/helpdesk",
                "X-Title": "Campus Helpdesk",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                return self._extract_openrouter_text(res_json)
        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                error_body = err.read().decode("utf-8")
            except Exception:
                pass
            msg = f"OpenRouter API returned status {err.code}: {err.reason}. {error_body}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except urllib.error.URLError as err:
            msg = f"OpenRouter API connection failed: {err.reason}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except TimeoutError as err:
            msg = f"OpenRouter API request timed out after {self.timeout_seconds}s"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except json.JSONDecodeError as err:
            msg = f"Failed to parse OpenRouter API JSON response: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except Exception as err:
            msg = f"Unexpected cloud LLM error: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err

    def _extract_openrouter_text(self, res_json: dict) -> str:
        """Extract text content from OpenRouter API response structure."""
        try:
            choices = res_json.get("choices", [])
            if not choices:
                raise CloudLLMServiceError("OpenRouter API response contained no choices.")

            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
            if not content:
                raise CloudLLMServiceError("OpenRouter API returned empty text content.")

            return content
        except (KeyError, IndexError, TypeError) as err:
            raise CloudLLMServiceError(f"Malformed OpenRouter API response payload: {err}") from err

    def _generate_stream_gemini(self, prompt: str):
        """Call Google Gemini streamGenerateContent REST API using SSE."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_content = line_str[6:].strip()
                        if data_content == "[DONE]":
                            break
                        try:
                            res_json = json.loads(data_content)
                            text = self._extract_gemini_text(res_json)
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue
                        except CloudLLMServiceError:
                            continue
        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                error_body = err.read().decode("utf-8")
            except Exception:
                pass
            msg = f"Gemini API returned status {err.code}: {err.reason}. {error_body}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except urllib.error.URLError as err:
            msg = f"Gemini API connection failed: {err.reason}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except TimeoutError as err:
            msg = f"Gemini API request timed out after {self.timeout_seconds}s"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except Exception as err:
            msg = f"Unexpected cloud LLM streaming error: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err

    def _generate_stream_openrouter(self, prompt: str):
        """Call OpenRouter chat completion stream REST API using SSE."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 512,
            "stream": True,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/Ankit2429/helpdesk",
                "X-Title": "Campus Helpdesk",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_content = line_str[6:].strip()
                        if data_content == "[DONE]":
                            break
                        try:
                            res_json = json.loads(data_content)
                            choices = res_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                error_body = err.read().decode("utf-8")
            except Exception:
                pass
            msg = f"OpenRouter API returned status {err.code}: {err.reason}. {error_body}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except urllib.error.URLError as err:
            msg = f"OpenRouter API connection failed: {err.reason}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except TimeoutError as err:
            msg = f"OpenRouter API request timed out after {self.timeout_seconds}s"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
        except Exception as err:
            msg = f"Unexpected cloud LLM streaming error: {err}"
            logger.warning(msg)
            raise CloudLLMServiceError(msg) from err
