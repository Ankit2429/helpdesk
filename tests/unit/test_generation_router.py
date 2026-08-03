"""Unit tests for GenerationRouter routing, fallbacks, and feature flags."""

from unittest.mock import MagicMock, patch
import pytest

from campus_helpdesk.application.exceptions import CloudLLMServiceError
from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.llm.generation_router import GenerationRouter


@pytest.fixture
def mock_local_llm():
    local = MagicMock()
    local.generate.return_value = "Local LLM Response"
    local.generate_stream.return_value = iter(["Local ", "LLM ", "Stream"])
    return local


@pytest.fixture
def mock_cloud_llm():
    cloud = MagicMock()
    cloud.generate.return_value = "Cloud LLM Response"
    cloud.generate_stream.return_value = iter(["Cloud ", "LLM ", "Stream"])
    return cloud


@pytest.fixture
def mock_checker():
    checker = MagicMock()
    checker.is_online.return_value = True
    return checker


def test_router_disabled_passthrough(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates directly to local LLM when enable_router=False."""
    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=False,
    )

    result = router.generate("Test prompt")
    assert result == "Local LLM Response"
    mock_local_llm.generate.assert_called_once_with("Test prompt")
    mock_cloud_llm.generate.assert_not_called()
    mock_checker.is_online.assert_not_called()


def test_router_cloud_not_configured(mock_local_llm, mock_checker):
    """Verify router delegates to local LLM when cloud_llm_service is None."""
    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=None,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    result = router.generate("Test prompt")
    assert result == "Local LLM Response"
    mock_local_llm.generate.assert_called_once_with("Test prompt")
    mock_checker.is_online.assert_not_called()


def test_router_online_uses_cloud(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates to Cloud LLM when online and configured."""
    mock_checker.is_online.return_value = True

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    result = router.generate("Test prompt")
    assert result == "Cloud LLM Response"
    mock_cloud_llm.generate.assert_called_once_with("Test prompt")
    mock_local_llm.generate.assert_not_called()


def test_router_offline_uses_local(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates to Local LLM when connectivity_checker returns False."""
    mock_checker.is_online.return_value = False

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    result = router.generate("Test prompt")
    assert result == "Local LLM Response"
    mock_local_llm.generate.assert_called_once_with("Test prompt")
    mock_cloud_llm.generate.assert_not_called()


def test_router_cloud_failure_falls_back_to_local(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router catches CloudLLMServiceError and gracefully falls back to local LLM."""
    mock_checker.is_online.return_value = True
    mock_cloud_llm.generate.side_effect = CloudLLMServiceError("Gemini API connection timed out")

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    result = router.generate("Test prompt")
    assert result == "Local LLM Response"
    mock_cloud_llm.generate.assert_called_once_with("Test prompt")
    mock_local_llm.generate.assert_called_once_with("Test prompt")


def test_router_init_with_settings(mock_local_llm):
    """Verify router initializes settings and feature flag correctly."""
    settings = Settings(enable_cloud_llm_router=False)
    router = GenerationRouter(local_llm_service=mock_local_llm, settings=settings)
    assert router.enable_router is False


def test_router_stream_disabled_passthrough(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates streaming directly to local LLM when enable_router=False."""
    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=False,
    )

    tokens = list(router.generate_stream("Test prompt"))
    assert tokens == ["Local ", "LLM ", "Stream"]
    mock_local_llm.generate_stream.assert_called_once_with("Test prompt")
    mock_cloud_llm.generate_stream.assert_not_called()


def test_router_stream_online_uses_cloud(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates streaming to Cloud LLM when online and configured."""
    mock_checker.is_online.return_value = True

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    tokens = list(router.generate_stream("Test prompt"))
    assert tokens == ["Cloud ", "LLM ", "Stream"]
    mock_cloud_llm.generate_stream.assert_called_once_with("Test prompt")
    mock_local_llm.generate_stream.assert_not_called()


def test_router_stream_offline_uses_local(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router delegates streaming to Local LLM when offline."""
    mock_checker.is_online.return_value = False

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    tokens = list(router.generate_stream("Test prompt"))
    assert tokens == ["Local ", "LLM ", "Stream"]
    mock_local_llm.generate_stream.assert_called_once_with("Test prompt")
    mock_cloud_llm.generate_stream.assert_not_called()


def test_router_stream_cloud_failure_falls_back_to_local(mock_local_llm, mock_cloud_llm, mock_checker):
    """Verify router catches CloudLLMServiceError during streaming and falls back to local LLM."""
    mock_checker.is_online.return_value = True
    mock_cloud_llm.generate_stream.side_effect = CloudLLMServiceError("Stream connection dropped")

    router = GenerationRouter(
        local_llm_service=mock_local_llm,
        cloud_llm_service=mock_cloud_llm,
        connectivity_checker=mock_checker,
        enable_router=True,
    )

    tokens = list(router.generate_stream("Test prompt"))
    assert tokens == ["Local ", "LLM ", "Stream"]
    mock_cloud_llm.generate_stream.assert_called_once_with("Test prompt")
    mock_local_llm.generate_stream.assert_called_once_with("Test prompt")
