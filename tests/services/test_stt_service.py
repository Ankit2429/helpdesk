"""
Tests for campus_helpdesk.services.stt_service
==============================================

Coverage:
1.  Mock transcription backend operation
2.  Service start, stop, shutdown lifecycle transitions
3.  Ingesting VOICE_STOPPED and publishing TRANSCRIPT_FINAL
4.  FIFO worker queue processing of multiple events
5.  Corrupted and empty audio files recovery handling (emitting ERROR)
6.  STT Diagnostics metrics collection
7.  Performance benchmarks (transcription latency < 1.0 second)
"""

from __future__ import annotations

import time
import uuid
import threading
import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    ErrorPayload,
    EventEnvelope,
    EventType,
    TranscriptPayload,
    VoicePayload,
)
from campus_helpdesk.services.stt_service import (
    MockTranscriptionBackend,
    STTService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_voice_stopped_event(path: str, chunk_id: str) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=EventType.VOICE_STOPPED,
        source="vad",
        payload=VoicePayload(
            audio_chunk_id=chunk_id,
            sample_rate=16000,
            duration_ms=1500,
            audio_segment_path=path,
        ),
        session_id="session-123",
    )


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-stt-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def mock_backend() -> MockTranscriptionBackend:
    return MockTranscriptionBackend(dummy_text="find library building")


@pytest.fixture
def stt(bus: EventBus, mock_backend: MockTranscriptionBackend) -> STTService:
    srv = STTService(event_bus=bus, backend=mock_backend, name="test-stt-service")
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Backend & Lifecycle
# ===========================================================================


class TestSTTLifecycle:
    def test_mock_backend_transcription(self, mock_backend: MockTranscriptionBackend) -> None:
        mock_backend.load_model()
        text, lang, confidence = mock_backend.transcribe("some_path.wav")
        assert text == "find library building"
        assert lang == "en"
        assert confidence == 0.96

    def test_start_stop_transitions(self, bus: EventBus, stt: STTService) -> None:
        assert stt.is_running() is False
        stt.start()
        assert stt.is_running() is True

        subs = bus.registered_subscribers()
        assert subs.get("VOICE_STOPPED", 0) == 1

        stt.stop()
        assert stt.is_running() is False
        subs = bus.registered_subscribers()
        assert subs.get("VOICE_STOPPED", 0) == 0


# ===========================================================================
# 2. Event Ingestion & Transcription
# ===========================================================================


class TestSTTTranscription:
    def test_transcribes_and_publishes_final(
        self, bus: EventBus, stt: STTService
    ) -> None:
        final_events: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [final_events.append(e), done.set()],
            EventType.TRANSCRIPT_FINAL,
            source="spy",
        )

        stt.start()
        bus.publish_sync(_make_voice_stopped_event("valid.wav", "chunk-456"))

        assert done.wait(timeout=3.0)
        assert len(final_events) == 1

        payload = final_events[0].payload
        assert isinstance(payload, TranscriptPayload)
        assert payload.text == "find library building"
        assert payload.language == "en"
        assert payload.confidence == 0.96
        assert payload.audio_chunk_id == "chunk-456"
        assert payload.duration_ms == 1500
        
        meta = final_events[0].get_metadata()
        assert "transcription_latency_ms" in meta
        assert meta["model_name"] == "mock-whisper-tiny"

    def test_error_on_corrupt_audio_file(
        self, bus: EventBus, stt: STTService
    ) -> None:
        error_events: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [error_events.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        stt.start()
        # MockTranscriptionBackend raises IOError when path contains "corrupt"
        bus.publish_sync(_make_voice_stopped_event("corrupt_audio.wav", "chunk-err"))

        assert done.wait(timeout=3.0)
        assert len(error_events) == 1
        
        payload = error_events[0].payload
        assert isinstance(payload, ErrorPayload)
        assert payload.service == "test-stt-service"
        assert "Corrupt audio" in payload.message
        assert payload.is_fatal is True


# ===========================================================================
# 3. FIFO Queue Ordering
# ===========================================================================


class TestFIFOQueue:
    def test_sequential_processing_under_load(
        self, bus: EventBus, stt: STTService
    ) -> None:
        processed_texts: list[str] = []
        done = threading.Event()

        def on_transcript(event: EventEnvelope) -> None:
            processed_texts.append(event.payload.text)
            if len(processed_texts) >= 5:
                done.set()

        bus.subscribe(on_transcript, EventType.TRANSCRIPT_FINAL, source="spy")

        stt.start()

        # Send 5 events in quick succession
        for i in range(5):
            bus.publish(_make_voice_stopped_event(f"path_{i}.wav", f"chunk_{i}"))

        assert done.wait(timeout=5.0)
        assert len(processed_texts) == 5
        # Diagnostics should report 5 processed files
        assert stt.diagnostics()["files_processed"] == 5


# ===========================================================================
# 4. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 100

    def test_transcription_overhead_latency(self, mock_backend: MockTranscriptionBackend) -> None:
        t0 = time.perf_counter()
        for _ in range(self.N):
            mock_backend.transcribe("normal.wav")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        print(
            f"\n[Benchmark] STT Transcription: {elapsed_ms:.1f} ms for {self.N} requests "
            f"(avg {avg_ms:.2f} ms/request)"
        )
        # Average transcription latency must be < 1.0 second (1000 ms)
        assert avg_ms < 1000.0
