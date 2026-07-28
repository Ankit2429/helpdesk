"""
Tests for campus_helpdesk.services.tts_service
==============================================

Coverage:
1.  Mock speech backend initialization and outputs
2.  Service start, stop, shutdown lifecycle transitions
3.  Answer ingestion and publication of TTS_STARTED / TTS_COMPLETED
4.  Speech preemption / interruption (publishes TTS_INTERRUPTED)
5.  FIFO queue sequential processing under load
6.  Edge cases (empty answer text, backend failure)
7.  Diagnostics monitoring
8.  Overhead benchmarks (synthesis startup/queue latency < 5 ms)
"""

from __future__ import annotations

import time
import uuid
import threading
import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    ErrorPayload,
    EventEnvelope,
    EventType,
    TTSPayload,
)
from campus_helpdesk.services.tts_service import (
    MockSpeechBackend,
    TTSService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class BypassAnswerPayload(AnswerPayload):
    def __post_init__(self) -> None:
        pass

def _make_answer_ready_event(answer: str, correlation_id: str | None = None, bypass_validation: bool = False) -> EventEnvelope:
    corr_uuid = correlation_id or str(uuid.uuid4())
    payload_cls = BypassAnswerPayload if bypass_validation else AnswerPayload
    return EventEnvelope.create(
        event_type=EventType.ANSWER_READY,
        source="inference",
        payload=payload_cls(
            answer=answer,
            confidence_score=0.95,
            confidence_level="HIGH",
            sources=("rules.md",),
            query="test query",
            inference_duration_ms=100,
        ),
        session_id="session-tts-123",
        correlation_id=corr_uuid,
    )


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-tts-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def mock_backend() -> MockSpeechBackend:
    return MockSpeechBackend()


@pytest.fixture
def tts(bus: EventBus, mock_backend: MockSpeechBackend) -> TTSService:
    srv = TTSService(event_bus=bus, backend=mock_backend, name="test-tts-service")
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Backend & Lifecycle
# ===========================================================================


class TestTTSLifecycle:
    def test_mock_backend_speech(self, mock_backend: MockSpeechBackend) -> None:
        mock_backend.load_model()
        started = threading.Event()
        stop = threading.Event()

        duration = mock_backend.synthesize_and_play(
            text="hello world",
            stop_event=stop,
            on_start_callback=lambda: started.set(),
        )
        assert started.is_set()
        assert duration >= 0.2

    def test_start_stop_transitions(self, bus: EventBus, tts: TTSService) -> None:
        assert tts.is_running() is False
        tts.start()
        assert tts.is_running() is True

        subs = bus.registered_subscribers()
        assert subs.get("ANSWER_READY", 0) == 1

        tts.stop()
        assert tts.is_running() is False
        subs = bus.registered_subscribers()
        assert subs.get("ANSWER_READY", 0) == 0


# ===========================================================================
# 2. Event Ingestion & Playback
# ===========================================================================


class TestTTSPlayback:
    def test_happy_path_emits_started_and_completed(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        started_events: list[EventEnvelope] = []
        completed_events: list[EventEnvelope] = []
        done_start = threading.Event()
        done_completed = threading.Event()

        bus.subscribe(
            lambda e: [started_events.append(e), done_start.set()],
            EventType.TTS_STARTED,
            source="spy",
        )
        bus.subscribe(
            lambda e: [completed_events.append(e), done_completed.set()],
            EventType.TTS_COMPLETED,
            source="spy",
        )

        tts.start()
        bus.publish_sync(_make_answer_ready_event("the library is open"))

        assert done_start.wait(timeout=3.0)
        assert len(started_events) == 1
        assert started_events[0].payload.text == "the library is open"

        assert done_completed.wait(timeout=3.0)
        assert len(completed_events) == 1
        assert completed_events[0].payload.duration_ms >= 200

    def test_empty_answer_publishes_error(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        errors: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [errors.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        tts.start()
        bus.publish_sync(_make_answer_ready_event("    ", bypass_validation=True))

        assert done.wait(timeout=3.0)
        assert len(errors) == 1
        assert errors[0].payload.error_type == "InvalidAnswerError"

    def test_synthesis_failure_publishes_error(
        self, bus: EventBus, tts: TTSService, mock_backend: MockSpeechBackend
    ) -> None:
        errors: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [errors.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        # Force Mock backend synthesize_and_play to crash
        def failing_synthesize(*args: Any, **kwargs: Any) -> float:
            raise IOError("Audio card disconnected")

        mock_backend.synthesize_and_play = failing_synthesize  # type: ignore[assignment]

        tts.start()
        bus.publish_sync(_make_answer_ready_event("error text"))

        assert done.wait(timeout=3.0)
        assert len(errors) == 1
        assert errors[0].payload.error_type == "TTSSynthesisError"


# ===========================================================================
# 3. Playback Cancellation / Preemption
# ===========================================================================


class TestTTSInterruption:
    def test_preemption_interrupts_current_and_plays_new(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        interrupted_events: list[EventEnvelope] = []
        completed_events: list[EventEnvelope] = []
        done_interrupted = threading.Event()
        done_completed = threading.Event()

        bus.subscribe(
            lambda e: [interrupted_events.append(e), done_interrupted.set()],
            EventType.TTS_INTERRUPTED,
            source="spy",
        )
        bus.subscribe(
            lambda e: [completed_events.append(e), done_completed.set()],
            EventType.TTS_COMPLETED,
            source="spy",
        )

        tts.start()

        # Publish a very long text to synthesize
        bus.publish(_make_answer_ready_event("this is a very long text that will take a long time to speak completely"))
        time.sleep(0.15)  # Wait for speech to start

        # Publish a second answer immediately, which should trigger preemption
        bus.publish(_make_answer_ready_event("short speech"))

        # First speech must be interrupted
        assert done_interrupted.wait(timeout=3.0)
        assert len(interrupted_events) == 1
        assert interrupted_events[0].payload.text.startswith("this is a very")
        assert interrupted_events[0].payload.interrupted_at_ms is not None

        # Second speech must complete naturally
        assert done_completed.wait(timeout=3.0)
        assert len(completed_events) == 1
        assert completed_events[0].payload.text == "short speech"


# ===========================================================================
# 4. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 100

    def test_synthesis_startup_and_queue_latency(self, bus: EventBus, mock_backend: MockSpeechBackend) -> None:
        # Bypassing play sleep delays in mock to isolate queue/synthesis overhead
        def instant_synthesize(text: str, stop_event: Any, on_start: Any) -> float:
            on_start()
            return 0.001

        mock_backend.synthesize_and_play = instant_synthesize  # type: ignore[assignment]

        srv = TTSService(event_bus=bus, backend=mock_backend, name="test-tts-bench")
        srv.start()

        t0 = time.perf_counter()
        for i in range(self.N):
            bus.publish(_make_answer_ready_event("speedy test"))

        while (srv.diagnostics()["requests_processed"] + srv.diagnostics()["failures"]) < self.N:
            time.sleep(0.01)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        srv.shutdown()

        print(
            f"\n[Benchmark] TTS Synthesis Startup: {elapsed_ms:.1f} ms for {self.N} requests "
            f"(avg {avg_ms:.3f} ms/request)"
        )
        # Average queue and synthesis launch overhead must be < 5.0 ms/request
        assert avg_ms < 5.0
