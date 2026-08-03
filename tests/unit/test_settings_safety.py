"""Unit tests for Settings model validation and safety warnings."""

import logging
import pytest
from campus_helpdesk.config.settings import Settings


def test_settings_offline_model_safety_warning(monkeypatch, caplog):
    """Verify warning is logged if OFFLINE_LLM_MODEL is 1.5b with ENABLE_CONTEXT_COMPOSER=False."""
    monkeypatch.setenv("OFFLINE_LLM_MODEL", "qwen2.5:1.5b")
    monkeypatch.setenv("ENABLE_CONTEXT_COMPOSER", "false")
    with caplog.at_level(logging.WARNING):
        settings = Settings()
        assert "UNHEALTHY RAG CONFIGURATION DETECTED" in caplog.text
        assert "OFFLINE_LLM_MODEL='qwen2.5:1.5b' with ENABLE_CONTEXT_COMPOSER=False" in caplog.text


def test_settings_offline_model_safety_no_warning(monkeypatch, caplog):
    """Verify no warning is logged when model is 3b or ContextComposer is True."""
    monkeypatch.setenv("OFFLINE_LLM_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("ENABLE_CONTEXT_COMPOSER", "false")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        settings = Settings()
        assert "UNHEALTHY RAG CONFIGURATION DETECTED" not in caplog.text
