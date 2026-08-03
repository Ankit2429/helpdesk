"""Unit tests for CloudLLMService text generation and SSE streaming."""

import io
from unittest.mock import MagicMock, patch
import pytest

from campus_helpdesk.application.exceptions import CloudLLMServiceError
from campus_helpdesk.infrastructure.llm.cloud_llm_service import CloudLLMService


def test_cloud_llm_missing_api_key():
    """Verify error is raised if API key is missing."""
    service = CloudLLMService(api_key="", provider="gemini")
    with pytest.raises(CloudLLMServiceError, match="API key is not configured"):
        service.generate("Hello")

    with pytest.raises(CloudLLMServiceError, match="API key is not configured"):
        list(service.generate_stream("Hello"))


@patch("urllib.request.urlopen")
def test_cloud_llm_gemini_generate_stream(mock_urlopen):
    """Verify Gemini SSE stream parsing yields text tokens correctly."""
    sse_response_bytes = (
        b'data: {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}\n\n'
        b'data: {"candidates": [{"content": {"parts": [{"text": "world!"}]}}]}\n\n'
        b'data: [DONE]\n\n'
    )
    mock_resp = io.BytesIO(sse_response_bytes)
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    service = CloudLLMService(api_key="test-key", provider="gemini")
    tokens = list(service.generate_stream("Test Gemini stream"))

    assert tokens == ["Hello", "world!"]


@patch("urllib.request.urlopen")
def test_cloud_llm_openrouter_generate_stream(mock_urlopen):
    """Verify OpenRouter SSE stream parsing yields text tokens correctly."""
    sse_response_bytes = (
        b'data: {"choices": [{"delta": {"content": "Campus "}}]}\n\n'
        b'data: {"choices": [{"delta": {"content": "Helpdesk"}}]}\n\n'
        b'data: [DONE]\n\n'
    )
    mock_resp = io.BytesIO(sse_response_bytes)
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    service = CloudLLMService(api_key="test-key", provider="openrouter")
    tokens = list(service.generate_stream("Test OpenRouter stream"))

    assert tokens == ["Campus ", "Helpdesk"]
