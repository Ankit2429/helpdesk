"""Unit tests for robot_main CLI entry point and production runtime builder."""

from unittest.mock import MagicMock, patch
import pytest

from campus_helpdesk.robot_main import build_production_runtime
from campus_helpdesk.runtime.system_runtime import SystemRuntime


def test_build_production_runtime_mock_mode():
    """Verify runtime builder constructs a valid SystemRuntime in mock mode."""
    runtime = build_production_runtime(use_mock=True)
    assert isinstance(runtime, SystemRuntime)
    assert runtime.camera._use_mock_fallback is True
    assert runtime.vad._use_mock_fallback is True


def test_build_production_runtime_device_overrides():
    """Verify device index arguments override settings defaults."""
    runtime = build_production_runtime(
        use_mock=True,
        camera_index=2,
        mic_index=3,
        speaker_index=4,
    )
    assert runtime.camera._camera_index == 2
    assert runtime.vad._device_index == 3
