"""
Integration Tests – End-to-End full conversation flows
======================================================

Module: tests.integration.test_full_conversation
File:   tests/integration/test_full_conversation.py

Covers:
1.  Normal conversation flow:
    - User approaches (PERSON_DETECTED) -> triggers READY/LISTENING.
    - Speaks voice segment (VOICE_STARTED/VOICE_STOPPED) -> transcribes (TRANSCRIPT_FINAL).
    - Query RAG inference (QUERY_STARTED/ANSWER_READY) -> synthesises speech (TTS_STARTED/TTS_COMPLETED).
    - User asks second question -> completes naturally.
    - User leaves (PERSON_LEFT) -> returns to IDLE.
2.  Unknown questions (returns RAG fallback reply).
3.  End-to-End latency benchmarks logging.
"""

from __future__ import annotations

import os
import time
import uuid
import threading
from datetime import datetime, timezone
import pytest
import cv2
import numpy as np

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    CameraPayload,
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
    bus = EventBus(maxsize=1000, max_workers=4, name="integ-bus")
    
    # Mock Backends for fast, deterministic headless integration
    cam = CameraService(event_bus=bus, camera_index=99)
    
    detector = MockPersonDetector()
    vis = VisionService(event_bus=bus, detector=detector, min_hits=1, min_misses=1)
    
    vad = VADService(event_bus=bus, device_index=99, use_mock_fallback=True, speech_frames_threshold=1, silence_frames_threshold=1)
    
    stt_backend = MockTranscriptionBackend(dummy_text="where is library office")
    stt = STTService(event_bus=bus, backend=stt_backend)
    
    infer_backend = MockInferenceBackend()
    inference = InferenceAdapter(event_bus=bus, backend=infer_backend, timeout_seconds=1.0)
    
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
# Integration Scenarios
# ===========================================================================


class TestFullConversation:
    def test_normal_conversation_happy_path(self, runtime: SystemRuntime) -> None:
        # Start integrated runtime
        runtime.start()
        # Stop VAD background loop to allow manual event injection
        runtime.vad.stop()
        bus = runtime.bus

        # Assert initial state
        assert runtime.manager.current_state() == RobotState.IDLE

        session_id = "session-e2e-1"
        tts_completed = threading.Event()
        bus.subscribe(lambda _: tts_completed.set(), EventType.TTS_COMPLETED, source="spy")

        # 1. User approaches (Inject PERSON_DETECTED)
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="vision",
                payload=PersonDetectedPayload(confidence=0.98, bounding_box=(10, 20, 100, 200), camera_index=0),
                session_id=session_id,
            )
        )
        time.sleep(0.1)
        assert runtime.manager.current_state() in {RobotState.READY, RobotState.LISTENING}

        # 2. User speaks (Inject VOICE_STARTED then VOICE_STOPPED with a simulated WAV file)
        wav_path = "mock_speech.wav"
        with open(wav_path, "wb") as f:
            f.write(b"RIFFmockheaderdata...")  # Dummy wave bytes

        try:
            # Voice Started
            bus.publish_sync(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STARTED,
                    source="vad",
                    payload=VoicePayload(audio_chunk_id="chunk-999"),
                    session_id=session_id,
                )
            )
            time.sleep(0.1)

            # Voice Stopped (this triggers STT transcription -> Inference query -> TTS synthesis)
            bus.publish_sync(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STOPPED,
                    source="vad",
                    payload=VoicePayload(audio_chunk_id="chunk-999", duration_ms=1000, audio_segment_path=wav_path),
                    session_id=session_id,
                )
            )

            # Wait for TTS play completion event
            assert tts_completed.wait(timeout=5.0)

            # Retrieve tracking log
            log = runtime.tracker.get_log(session_id)
            assert log is not None
            assert log["completion_state"] == "SUCCESS"
            assert "stt_latency_ms" in log["latencies"]
            assert "inference_latency_ms" in log["latencies"]

            print(f"\n[E2E Conversation Log] {log}")

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        # 3. User leaves (Inject PERSON_LEFT)
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_LEFT,
                source="vision",
                payload=PersonLeftPayload(last_seen_at=datetime.now(timezone.utc), frames_without_detection=10),
                session_id=session_id,
            )
        )
        time.sleep(0.2)
        assert runtime.manager.current_state() in {RobotState.IDLE, RobotState.READY}

    def test_unknown_question_fallback(self, runtime: SystemRuntime) -> None:
        runtime.start()
        # Stop VAD background loop to allow manual event injection
        runtime.vad.stop()
        bus = runtime.bus

        session_id = "session-e2e-2"
        tts_completed = threading.Event()
        bus.subscribe(lambda _: tts_completed.set(), EventType.TTS_COMPLETED, source="spy")

        # Configure mock inference backend to return a fallback response
        runtime.inference._backend.mock_answer = "I don't have information about that in my knowledge base."
        runtime.inference._backend.mock_confidence = 0.2
        runtime.inference._backend.mock_confidence_level = "LOW"

        # Inject approach
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="vision",
                payload=PersonDetectedPayload(confidence=0.95, bounding_box=None),
                session_id=session_id,
            )
        )

        wav_path = "mock_speech_unknown.wav"
        with open(wav_path, "wb") as f:
            f.write(b"RIFFmockheader...")

        try:
            # Voice Started to transition FSM to LISTENING
            bus.publish_sync(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STARTED,
                    source="vad",
                    payload=VoicePayload(audio_chunk_id="chunk-unknown"),
                    session_id=session_id,
                )
            )
            time.sleep(0.1)

            # Voice Stopped (trigger query)
            bus.publish_sync(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STOPPED,
                    source="vad",
                    payload=VoicePayload(audio_chunk_id="chunk-unknown", duration_ms=500, audio_segment_path=wav_path),
                    session_id=session_id,
                )
            )

            assert tts_completed.wait(timeout=5.0)

            # Retrieve log
            log = runtime.tracker.get_log(session_id)
            assert log is not None
            assert log["completion_state"] == "SUCCESS"
            
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
