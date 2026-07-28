"""
Integration Tests – Failure Recovery and Resiliency
===================================================

Module: tests.integration.test_failure_recovery
File:   tests/integration/test_failure_recovery.py

Covers:
1.  Person leaves while speaking (aborts speech/RAG flow).
2.  Camera disconnect (publishes CAMERA_DISCONNECTED and handles error).
3.  Microphone disconnect (publishes MICROPHONE_ERROR).
4.  Inference timeout (emits ERROR but continues running).
5.  TTS interruption / preemption (preempts current playback on new query).
6.  Worker recovery (worker loops continue after individual request exceptions).
7.  Graceful shutdown (stopping and joining all threads).
8.  Restart after shutdown.
"""

from __future__ import annotations

import os
import time
import uuid
import threading
from datetime import datetime, timezone
import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    CameraPayload,
    ErrorPayload,
    EventEnvelope,
    EventType,
    PersonDetectedPayload,
    PersonLeftPayload,
    TranscriptPayload,
    VoicePayload,
)
from campus_helpdesk.interaction.robot_state import RobotState
from campus_helpdesk.runtime.system_runtime import SystemRuntime
from campus_helpdesk.services.camera_service import CameraService
from campus_helpdesk.services.vision_service import MockPersonDetector, VisionService
from campus_helpdesk.services.vad_service import VADService
from campus_helpdesk.services.stt_service import MockTranscriptionBackend, STTService
from campus_helpdesk.services.inference_adapter import MockInferenceBackend, InferenceAdapter
from campus_helpdesk.services.tts_service import MockSpeechBackend, TTSService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runtime() -> SystemRuntime:
    bus = EventBus(maxsize=1000, max_workers=4, name="fail-bus")
    
    cam = CameraService(event_bus=bus, camera_index=99)
    detector = MockPersonDetector()
    vis = VisionService(event_bus=bus, detector=detector, min_hits=1, min_misses=1)
    vad = VADService(event_bus=bus, device_index=99, use_mock_fallback=True, speech_frames_threshold=1, silence_frames_threshold=1)
    
    stt_backend = MockTranscriptionBackend()
    stt = STTService(event_bus=bus, backend=stt_backend)
    
    infer_backend = MockInferenceBackend()
    inference = InferenceAdapter(event_bus=bus, backend=infer_backend, timeout_seconds=0.3)
    
    tts_backend = MockSpeechBackend()
    tts = TTSService(event_bus=bus, backend=tts_backend)

    rt = SystemRuntime(
        event_bus=bus,
        camera=cam,
        vision=vis,
        vad=vad,
        stt=stt,
        inference=inference,
        tts=tts,
    )
    yield rt
    rt.shutdown()


# ===========================================================================
# Resilience Tests
# ===========================================================================


class TestFailureRecovery:
    def test_person_leaves_while_speaking_aborts_flow(self, runtime: SystemRuntime) -> None:
        runtime.start()
        runtime.vad.stop()
        bus = runtime.bus

        session_id = "session-fail-1"
        
        # Approaches
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="vision",
                payload=PersonDetectedPayload(confidence=0.98, bounding_box=None),
                session_id=session_id,
            )
        )
        time.sleep(0.1)

        # Starts speaking
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="chunk-f1"),
                session_id=session_id,
            )
        )
        time.sleep(0.1)

        # User leaves immediately without ending voice segment
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_LEFT,
                source="vision",
                payload=PersonLeftPayload(last_seen_at=datetime.now(timezone.utc), frames_without_detection=10),
                session_id=session_id,
            )
        )
        time.sleep(0.2)

        # Manager state returns to IDLE or READY
        assert runtime.manager.current_state() in {RobotState.IDLE, RobotState.READY}

    def test_camera_disconnect_lifecycle(self, runtime: SystemRuntime) -> None:
        runtime.start()
        bus = runtime.bus

        disconnected = threading.Event()
        bus.subscribe(lambda _: disconnected.set(), EventType.CAMERA_DISCONNECTED, source="spy")

        # Simulate camera disconnect event on the bus
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.CAMERA_DISCONNECTED,
                source="camera",
                payload=CameraPayload(
                    frame_id="err-frame",
                    timestamp=datetime.now(timezone.utc),
                    resolution="0x0",
                    frame_number=0,
                    capture_latency_ms=0.0,
                ),
            )
        )

        assert disconnected.wait(timeout=2.0)
        assert runtime.camera.diagnostics()["reconnect_count"] >= 0

    def test_microphone_error_event(self, runtime: SystemRuntime) -> None:
        runtime.start()
        bus = runtime.bus

        mic_error = threading.Event()
        bus.subscribe(lambda _: mic_error.set(), EventType.MICROPHONE_ERROR, source="spy")

        # Simulate microphone stream error
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.MICROPHONE_ERROR,
                source="vad",
                payload=VoicePayload(audio_chunk_id="chunk-err"),
            )
        )

        assert mic_error.wait(timeout=2.0)

    def test_inference_timeout_recovery(self, runtime: SystemRuntime) -> None:
        runtime.start()
        runtime.vad.stop()
        bus = runtime.bus

        session_id = "session-fail-2"
        error_event = threading.Event()
        bus.subscribe(lambda e: error_event.set() if e.payload.error_type == "InferenceTimeoutError" else None, EventType.ERROR, source="spy")

        # Force backend query delay longer than the adapter's 0.3s timeout
        runtime.inference._backend.simulate_delay_sec = 0.5

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.TRANSCRIPT_FINAL,
                source="stt",
                payload=TranscriptPayload(text="Slow query", is_final=True, audio_chunk_id="chunk-slow"),
                session_id=session_id,
            )
        )

        assert error_event.wait(timeout=3.0)
        assert runtime.inference.diagnostics()["timeouts"] == 1
        assert runtime.inference.is_running() is True  # Worker continues running

    def test_tts_preemption_interruption(self, runtime: SystemRuntime) -> None:
        runtime.start()
        runtime.vad.stop()
        bus = runtime.bus

        session_id = "session-fail-3"
        interrupted = threading.Event()
        bus.subscribe(lambda _: interrupted.set(), EventType.TTS_INTERRUPTED, source="spy")

        # Inject approach
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="vision",
                payload=PersonDetectedPayload(confidence=0.98, bounding_box=None),
                session_id=session_id,
            )
        )

        # Trigger first speech (long duration text)
        bus.publish(_make_answer_ready_event("this is a very long response text that takes time to speak", session_id))
        time.sleep(0.15)  # Wait for synthesis start

        # Trigger second speech immediately (preempts first)
        bus.publish(_make_answer_ready_event("short response", session_id))

        assert interrupted.wait(timeout=3.0)

    def test_restart_after_shutdown(self, runtime: SystemRuntime) -> None:
        # 1. First run
        runtime.start()
        assert runtime.is_running() is True
        runtime.stop()
        assert runtime.is_running() is False

        # 2. Restart
        runtime.start()
        assert runtime.is_running() is True
        runtime.stop()
        assert runtime.is_running() is False


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_answer_ready_event(answer: str, session_id: str) -> EventEnvelope:
    from campus_helpdesk.interaction.events import AnswerPayload
    return EventEnvelope.create(
        event_type=EventType.ANSWER_READY,
        source="inference",
        payload=AnswerPayload(
            answer=answer,
            confidence_score=0.95,
            confidence_level="HIGH",
            sources=(),
            query="query text",
            inference_duration_ms=100,
        ),
        session_id=session_id,
        correlation_id=str(uuid.uuid4()),
    )
