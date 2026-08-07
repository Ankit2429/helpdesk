"""Unit tests for robot_main CLI entry point and production runtime builder."""

from unittest.mock import MagicMock, patch
import pytest

from campus_helpdesk.robot_main import build_production_runtime
from campus_helpdesk.runtime.system_runtime import SystemRuntime


def test_build_production_runtime_mock_mode():
    """Verify runtime builder constructs a valid SystemRuntime in mock mode."""
    runtime = build_production_runtime(use_mock=True)
    assert isinstance(runtime, SystemRuntime)
    # VAD is now a local service in build_production_runtime, not a SystemRuntime attribute.
    # Verify the components that are on SystemRuntime are correctly wired.
    assert runtime.stt is not None
    assert runtime.tts is not None
    if runtime.camera is not None:
        assert runtime.camera._use_mock_fallback is True


def test_build_production_runtime_device_overrides():
    """Verify device index arguments are accepted without error."""
    runtime = build_production_runtime(
        use_mock=True,
        camera_index=2,
        mic_index=3,
        speaker_index=4,
    )
    assert isinstance(runtime, SystemRuntime)
    # VAD device_index is handled inside build_production_runtime when ENABLE_VAD=true.
    # When disabled (default), no VAD attribute is present on the runtime.
    if runtime.camera is not None:
        assert runtime.camera._camera_index == 2
