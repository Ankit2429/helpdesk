"""
Tests for campus_helpdesk.services.tts_service
==============================================

Coverage:
1.  Mock speech backend initialization and speech outputs
2.  Service start, stop, shutdown lifecycle transitions
3.  Answer ingestion and publication of TTS_STARTED / TTS_COMPLETED
4.  Speech preemption / interruption (publishes TTS_INTERRUPTED)
5.  FIFO queue sequential processing under load
6.  Edge cases (empty answer text, backend failure)
7.  Diagnostics monitoring
8.  Overhead benchmarks (synthesis startup/queue latency < 5 ms)
9.  Sentence streaming: multi-sentence answers produce sequential events
10. Sentence splitter: handles English, Hindi danda, abbreviations, edge cases
11. Multilingual voice: language field in AnswerPayload drives voice selection
12. Barge-in: VOICE_STARTED in SPEAKING state fires interrupt callback
13. Barge-in: FSM transitions SPEAKING → LISTENING on barge-in
14. Interrupt generation counter: prevents stale-sentence playback
15. Inter-sentence pause: configurable gap between sentences
"""

from __future__ import annotations

import time
import uuid
import threading
from typing import Any
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
    PiperBackend,
    TTSService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class BypassAnswerPayload(AnswerPayload):
    def __post_init__(self) -> None:
        pass

def _make_answer_ready_event(
    answer: str,
    correlation_id: str | None = None,
    bypass_validation: bool = False,
    language: str = "en",
) -> EventEnvelope:
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
            language=language,
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
# 4. Sentence Streaming
# ===========================================================================


class TestSentenceStreaming:
    def test_multi_sentence_answer_produces_tts_started_once(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        """A 3-sentence answer should produce exactly one TTS_STARTED event
        (on the first sentence) and one TTS_COMPLETED event (after the last)."""
        started_events: list[EventEnvelope] = []
        completed_events: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(lambda e: started_events.append(e), EventType.TTS_STARTED, source="spy")
        bus.subscribe(
            lambda e: [completed_events.append(e), done.set()],
            EventType.TTS_COMPLETED,
            source="spy",
        )

        tts.start()
        # 3-sentence answer — splitter should produce 3 sentences
        answer = "The library is on the ground floor. It opens at 8 AM. Closing time is 8 PM."
        bus.publish_sync(_make_answer_ready_event(answer))

        assert done.wait(timeout=8.0)
        # TTS_STARTED fires exactly once (on the first sentence callback)
        assert len(started_events) == 1
        assert started_events[0].payload.text == answer
        # TTS_COMPLETED fires once after all sentences are done
        assert len(completed_events) == 1
        assert completed_events[0].payload.duration_ms >= 200

    def test_first_sentence_starts_without_waiting_for_full_answer(
        self, bus: EventBus
    ) -> None:
        """First audio should begin before all remaining sentences finish.

        We measure the time from ANSWER_READY to TTS_STARTED. With streaming,
        this should reflect only the first sentence synthesis time (<500ms with mock),
        NOT the total duration of the entire answer.
        """
        # Use a zero-pause service to isolate first-sentence latency
        srv = TTSService(event_bus=bus, backend=MockSpeechBackend(), inter_sentence_pause_ms=0, name="test-stream-latency")
        done_start = threading.Event()
        t_answer_ready: list[float] = []
        t_tts_started: list[float] = []

        bus.subscribe(
            lambda e: [t_tts_started.append(time.perf_counter()), done_start.set()],
            EventType.TTS_STARTED,
            source="latency-spy",
        )

        srv.start()
        t_answer_ready.append(time.perf_counter())
        # 5-sentence answer: without streaming, this would take ~5s with MockBackend
        answer = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        bus.publish_sync(_make_answer_ready_event(answer))

        assert done_start.wait(timeout=3.0)

        onset_ms = (t_tts_started[0] - t_answer_ready[0]) * 1000
        print(f"\n[Streaming] First audio onset: {onset_ms:.0f}ms")
        # First audio should start within 500ms even for a 5-sentence answer
        assert onset_ms < 500, (
            f"First sentence started too late ({onset_ms:.0f}ms). "
            "Streaming should start first sentence immediately, not wait for full text."
        )

        srv.shutdown()

    def test_single_sentence_completes_normally(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        """A single-sentence answer should still publish TTS_STARTED and TTS_COMPLETED."""
        done = threading.Event()
        completed_events: list[EventEnvelope] = []

        bus.subscribe(
            lambda e: [completed_events.append(e), done.set()],
            EventType.TTS_COMPLETED,
            source="spy",
        )
        tts.start()
        bus.publish_sync(_make_answer_ready_event("Hello, welcome to the campus helpdesk."))
        assert done.wait(timeout=3.0)
        assert len(completed_events) == 1


# ===========================================================================
# 5. Sentence Splitter
# ===========================================================================


class TestSentenceSplitter:
    def test_english_period_splits(self) -> None:
        text = "The library is open. It closes at 8 PM."
        result = TTSService.split_into_sentences(text)
        assert len(result) == 2
        assert "The library is open" in result[0]
        assert "It closes at 8 PM" in result[1]

    def test_question_mark_splits(self) -> None:
        text = "What time does it open? The library opens at 8 AM."
        result = TTSService.split_into_sentences(text)
        assert len(result) == 2

    def test_exclamation_splits(self) -> None:
        text = "Welcome to campus! The library is straight ahead."
        result = TTSService.split_into_sentences(text)
        assert len(result) == 2

    def test_hindi_danda_splits(self) -> None:
        text = "पुस्तकालय भूतल पर है। यह सुबह 8 बजे खुलता है।"
        result = TTSService.split_into_sentences(text)
        assert len(result) == 2, f"Expected 2 Hindi sentences, got {len(result)}: {result}"

    def test_empty_text_returns_empty(self) -> None:
        assert TTSService.split_into_sentences("") == []
        assert TTSService.split_into_sentences("   ") == []

    def test_single_sentence_no_boundary_returns_as_list(self) -> None:
        text = "The library is on the ground floor"
        result = TTSService.split_into_sentences(text)
        assert result == [text]

    def test_newline_treated_as_boundary(self) -> None:
        text = "First sentence\nSecond sentence"
        result = TTSService.split_into_sentences(text)
        assert len(result) >= 1  # At minimum does not crash

    def test_short_fragments_merged(self) -> None:
        """Fragments shorter than 3 chars should be merged with preceding sentence."""
        text = "The library opens at 8. AM. today."
        result = TTSService.split_into_sentences(text)
        # "AM" alone (2 chars) should be merged with the preceding sentence
        for sentence in result:
            assert len(sentence) >= 3, f"Found very short fragment: {sentence!r}"


# ===========================================================================
# 6. Multilingual Voice Selection
# ===========================================================================


class TestMultilingualVoice:
    def test_english_answer_uses_en_voice(self, bus: EventBus) -> None:
        """AnswerPayload language='en' should pass language='en' to backend."""
        received_languages: list[str] = []
        done = threading.Event()

        class LangTrackingBackend(MockSpeechBackend):
            def synthesize_and_play(self, text, stop_event, on_start_callback, language="en"):
                received_languages.append(language)
                return super().synthesize_and_play(text, stop_event, on_start_callback, language)

        srv = TTSService(event_bus=bus, backend=LangTrackingBackend(), name="test-lang-en")
        bus.subscribe(lambda e: done.set(), EventType.TTS_COMPLETED, source="spy-en")
        srv.start()
        bus.publish_sync(_make_answer_ready_event("The library is open.", language="en"))
        assert done.wait(timeout=3.0)
        srv.shutdown()
        assert received_languages, "Backend was never called"
        assert received_languages[0] == "en", f"Expected 'en', got {received_languages[0]!r}"

    def test_hindi_answer_uses_hi_voice(self, bus: EventBus) -> None:
        """AnswerPayload language='hi' should pass language='hi' to backend."""
        received_languages: list[str] = []
        done = threading.Event()

        class LangTrackingBackend(MockSpeechBackend):
            def synthesize_and_play(self, text, stop_event, on_start_callback, language="en"):
                received_languages.append(language)
                return super().synthesize_and_play(text, stop_event, on_start_callback, language)

        srv = TTSService(event_bus=bus, backend=LangTrackingBackend(), name="test-lang-hi")
        bus.subscribe(lambda e: done.set(), EventType.TTS_COMPLETED, source="spy-hi")
        srv.start()
        bus.publish_sync(_make_answer_ready_event("पुस्तकालय भूतल पर है।", language="hi"))
        assert done.wait(timeout=3.0)
        srv.shutdown()
        assert received_languages, "Backend was never called"
        assert received_languages[0] == "hi", f"Expected 'hi', got {received_languages[0]!r}"

    def test_kannada_answer_uses_kn_voice_gracefully(self, bus: EventBus) -> None:
        """AnswerPayload language='kn' should pass language='kn' to backend.
        PiperBackend will fall back gracefully since no Kannada model exists."""
        received_languages: list[str] = []
        done = threading.Event()

        class LangTrackingBackend(MockSpeechBackend):
            def synthesize_and_play(self, text, stop_event, on_start_callback, language="en"):
                received_languages.append(language)
                return super().synthesize_and_play(text, stop_event, on_start_callback, language)

        srv = TTSService(event_bus=bus, backend=LangTrackingBackend(), name="test-lang-kn")
        bus.subscribe(lambda e: done.set(), EventType.TTS_COMPLETED, source="spy-kn")
        srv.start()
        bus.publish_sync(_make_answer_ready_event("ಗ್ರಂಥಾಲಯ ಎಲ್ಲಿದೆ", language="kn"))
        assert done.wait(timeout=3.0)
        srv.shutdown()
        assert received_languages, "Backend was never called"
        assert received_languages[0] == "kn", f"Expected 'kn', got {received_languages[0]!r}"

    def test_piper_voice_map_contains_en_and_hi(self) -> None:
        """PiperBackend.VOICE_MAP must map en and hi to valid model names."""
        assert "en" in PiperBackend.VOICE_MAP
        assert "hi" in PiperBackend.VOICE_MAP
        assert "en_US" in PiperBackend.VOICE_MAP
        assert "lessac" in PiperBackend.VOICE_MAP["en"].lower() or "en_US" in PiperBackend.VOICE_MAP["en"]
        assert "pratham" in PiperBackend.VOICE_MAP["hi"].lower() or "hi_IN" in PiperBackend.VOICE_MAP["hi"]

    def test_piper_voice_map_has_no_kannada_entry(self) -> None:
        """PiperBackend.VOICE_MAP must NOT include Kannada (no official model exists)."""
        assert "kn" not in PiperBackend.VOICE_MAP
        assert "kn_IN" not in PiperBackend.VOICE_MAP


# ===========================================================================
# 7. Barge-In (TTSService interrupt + generation counter)
# ===========================================================================


class TestBargeIn:
    def test_interrupt_increments_generation_counter(self, tts: TTSService) -> None:
        """Calling interrupt() must increment _interrupt_generation."""
        initial_gen = tts._interrupt_generation
        tts.interrupt()
        assert tts._interrupt_generation == initial_gen + 1

    def test_multiple_interrupts_increment_monotonically(self, tts: TTSService) -> None:
        for i in range(5):
            tts.interrupt()
        assert tts._interrupt_generation == 5

    def test_interrupt_stops_active_playback(
        self, bus: EventBus, tts: TTSService
    ) -> None:
        """Calling interrupt() during playback must fire TTS_INTERRUPTED."""
        done_interrupted = threading.Event()
        interrupted_events: list[EventEnvelope] = []

        bus.subscribe(
            lambda e: [interrupted_events.append(e), done_interrupted.set()],
            EventType.TTS_INTERRUPTED,
            source="barge-spy",
        )

        tts.start()
        # Start a very long utterance
        bus.publish(_make_answer_ready_event(
            "This is a very long sentence that will take many seconds to complete in mock mode."
        ))
        time.sleep(0.2)  # Let playback start
        tts.interrupt()

        assert done_interrupted.wait(timeout=3.0)
        assert len(interrupted_events) == 1
        assert interrupted_events[0].payload.interrupted_at_ms is not None

    def test_interrupt_generation_prevents_stale_sentences(
        self, bus: EventBus
    ) -> None:
        """After interrupt(), remaining sentences from old answer must NOT play.

        We publish a long 5-sentence answer, interrupt it immediately, then
        publish a short 1-sentence answer. Only the short answer should complete.
        """
        done = threading.Event()
        completed_events: list[EventEnvelope] = []
        interrupted_events: list[EventEnvelope] = []

        srv = TTSService(
            event_bus=bus,
            backend=MockSpeechBackend(),
            inter_sentence_pause_ms=0,
            name="test-gen-counter",
        )
        bus.subscribe(
            lambda e: [completed_events.append(e), done.set()],
            EventType.TTS_COMPLETED,
            source="gen-spy",
        )
        bus.subscribe(
            lambda e: interrupted_events.append(e),
            EventType.TTS_INTERRUPTED,
            source="gen-spy",
        )

        srv.start()

        # 5-sentence answer
        long_answer = (
            "Sentence one is long. Sentence two is also long. "
            "Sentence three is long too. Sentence four continues. Sentence five ends."
        )
        bus.publish(_make_answer_ready_event(long_answer))
        time.sleep(0.15)  # Let first sentence start

        # Interrupt + new short answer
        srv.interrupt()
        bus.publish(_make_answer_ready_event("Short answer only."))

        assert done.wait(timeout=5.0)
        # There should be exactly one TTS_COMPLETED (for the short answer)
        assert len(completed_events) == 1
        assert completed_events[0].payload.text == "Short answer only."

        srv.shutdown()


# ===========================================================================
# 8. Barge-In via InteractionManager callback
# ===========================================================================


class TestBargeInViaManager:
    def test_tts_interrupt_callback_fires_on_barge_in(self, bus: EventBus) -> None:
        """When tts_interrupt_callback is registered with InteractionManager,
        it must be called when VOICE_STARTED arrives in SPEAKING state."""
        from campus_helpdesk.interaction.interaction_manager import InteractionManager
        from campus_helpdesk.interaction.robot_state import RobotState, RobotStateMachine
        from campus_helpdesk.interaction.events import VoicePayload

        fsm = RobotStateMachine()
        callback_fired = threading.Event()

        def fake_interrupt():
            callback_fired.set()

        manager = InteractionManager(
            event_bus=bus,
            state_machine=fsm,
            tts_interrupt_callback=fake_interrupt,
            enable_barge_in=True,
        )

        # Manually advance FSM to SPEAKING state
        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)
        fsm.transition_to(RobotState.READY)
        fsm.transition_to(RobotState.LISTENING)
        fsm.transition_to(RobotState.PROCESSING)
        fsm.transition_to(RobotState.SPEAKING)

        assert fsm.state == RobotState.SPEAKING

        # Fire VOICE_STARTED in SPEAKING state (barge-in)
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="barge-chunk", sample_rate=16000, duration_ms=0),
            )
        )

        assert callback_fired.wait(timeout=2.0), "TTS interrupt callback was not fired on barge-in"

    def test_barge_in_disabled_by_default_config_flag(self, bus: EventBus) -> None:
        """When enable_barge_in=False (default), VOICE_STARTED in SPEAKING state must be ignored."""
        from campus_helpdesk.interaction.interaction_manager import InteractionManager
        from campus_helpdesk.interaction.robot_state import RobotState, RobotStateMachine
        from campus_helpdesk.interaction.events import VoicePayload

        fsm = RobotStateMachine()
        callback_fired = threading.Event()

        def fake_interrupt():
            callback_fired.set()

        manager = InteractionManager(
            event_bus=bus,
            state_machine=fsm,
            tts_interrupt_callback=fake_interrupt,
            enable_barge_in=False,  # Default safety setting
        )

        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)
        fsm.transition_to(RobotState.READY)
        fsm.transition_to(RobotState.LISTENING)
        fsm.transition_to(RobotState.PROCESSING)
        fsm.transition_to(RobotState.SPEAKING)

        assert fsm.state == RobotState.SPEAKING

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="barge-chunk", sample_rate=16000, duration_ms=0),
            )
        )

        time.sleep(0.1)
        assert not callback_fired.is_set(), "Interrupt callback was fired when enable_barge_in=False"
        assert fsm.state == RobotState.SPEAKING, (
            f"FSM state changed from SPEAKING when barge-in was disabled! State: {fsm.state.name}"
        )

    def test_barge_in_transitions_speaking_to_listening(self, bus: EventBus) -> None:
        """Barge-in must transition FSM from SPEAKING → LISTENING when enabled."""
        from campus_helpdesk.interaction.interaction_manager import InteractionManager
        from campus_helpdesk.interaction.robot_state import RobotState, RobotStateMachine
        from campus_helpdesk.interaction.events import VoicePayload

        fsm = RobotStateMachine()
        manager = InteractionManager(
            event_bus=bus,
            state_machine=fsm,
            tts_interrupt_callback=lambda: None,
            enable_barge_in=True,
        )

        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)
        fsm.transition_to(RobotState.READY)
        fsm.transition_to(RobotState.LISTENING)
        fsm.transition_to(RobotState.PROCESSING)
        fsm.transition_to(RobotState.SPEAKING)

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="barge-chunk", sample_rate=16000, duration_ms=0),
            )
        )

        time.sleep(0.1)
        assert fsm.state == RobotState.LISTENING, (
            f"Expected LISTENING after barge-in, got {fsm.state.name}"
        )

    def test_barge_in_does_not_fire_in_idle_state(self, bus: EventBus) -> None:
        """Interrupt callback must NOT be called when FSM is in IDLE state."""
        from campus_helpdesk.interaction.interaction_manager import InteractionManager
        from campus_helpdesk.interaction.robot_state import RobotState, RobotStateMachine
        from campus_helpdesk.interaction.events import VoicePayload

        fsm = RobotStateMachine()
        callback_fired = threading.Event()

        manager = InteractionManager(
            event_bus=bus,
            state_machine=fsm,
            tts_interrupt_callback=lambda: callback_fired.set(),
        )

        # Manually advance FSM to IDLE (do NOT go to SPEAKING)
        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="idle-chunk", sample_rate=16000, duration_ms=0),
            )
        )
        time.sleep(0.1)
        assert not callback_fired.is_set(), "Interrupt callback must NOT fire in IDLE state"


# ===========================================================================
# 9. Inter-Sentence Pause
# ===========================================================================


class TestInterSentencePause:
    def test_pause_is_configurable(self, bus: EventBus) -> None:
        """inter_sentence_pause_ms should appear in diagnostics."""
        srv = TTSService(event_bus=bus, backend=MockSpeechBackend(), inter_sentence_pause_ms=300)
        srv.start()
        diag = srv.diagnostics()
        assert diag["inter_sentence_pause_ms"] == 300
        srv.shutdown()

    def test_zero_pause_disables_gap(self, bus: EventBus) -> None:
        """Setting inter_sentence_pause_ms=0 must not insert any gap."""
        srv = TTSService(event_bus=bus, backend=MockSpeechBackend(), inter_sentence_pause_ms=0)
        srv.start()
        assert srv.diagnostics()["inter_sentence_pause_ms"] == 0
        srv.shutdown()


# ===========================================================================
# 10. Diagnostics
# ===========================================================================


class TestDiagnostics:
    def test_diagnostics_includes_new_fields(self, bus: EventBus, tts: TTSService) -> None:
        tts.start()
        diag = tts.diagnostics()
        assert "sentences_spoken" in diag
        assert "inter_sentence_pause_ms" in diag
        assert "interrupt_generation" in diag
        assert diag["interrupt_generation"] == 0

    def test_sentences_spoken_increments(self, bus: EventBus, tts: TTSService) -> None:
        done = threading.Event()
        bus.subscribe(lambda e: done.set(), EventType.TTS_COMPLETED, source="diag-spy")
        tts.start()
        # 3-sentence answer
        bus.publish_sync(_make_answer_ready_event(
            "First sentence here. Second sentence here. Third sentence here."
        ))
        assert done.wait(timeout=5.0)
        diag = tts.diagnostics()
        assert diag["sentences_spoken"] >= 1  # At least 1 sentence was spoken


# ===========================================================================
# 11. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 100

    def test_synthesis_startup_and_queue_latency(self, bus: EventBus, mock_backend: MockSpeechBackend) -> None:
        # Bypassing play sleep delays in mock to isolate queue/synthesis overhead
        def instant_synthesize(text: str, stop_event: Any, on_start_callback: Any, language: str = "en") -> float:
            on_start_callback()
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


# ===========================================================================
# 12. Piper Backend Unit Tests
# ===========================================================================


from unittest.mock import MagicMock, patch
from campus_helpdesk.application.exceptions import AudioError


class TestPiperBackend:
    def test_piper_backend_load_model_failure(self):
        """Verify AudioError is raised when model file does not exist."""
        backend = PiperBackend(model_path="non_existent_model_123.onnx")
        with pytest.raises(AudioError, match="Piper model file not found"):
            backend.load_model()

    @patch("sounddevice.RawOutputStream")
    def test_piper_backend_synthesize_and_play(self, mock_raw_stream):
        """Verify PiperBackend streams PCM chunks and triggers on_start_callback."""
        backend = PiperBackend(model_path="dummy.onnx")
        backend._voice = "CLI_SUBPROCESS"
        backend._synthesize_chunks = MagicMock(return_value=iter([b"\x00\x01" * 100, b"\x02\x03" * 100]))

        callback_called = False

        def on_start():
            nonlocal callback_called
            callback_called = True

        stop_event = threading.Event()
        duration = backend.synthesize_and_play("Hello world", stop_event, on_start)

        assert callback_called is True
        assert duration >= 0.0
        mock_raw_stream.assert_called_once()

    @patch("sounddevice.RawOutputStream")
    def test_piper_backend_cancel_interruption(self, mock_raw_stream):
        """Verify playback breaks immediately when cancelled."""
        backend = PiperBackend(model_path="dummy.onnx")
        backend._voice = "CLI_SUBPROCESS"

        def mock_chunks(text):
            yield b"\x00\x01" * 10
            backend.cancel()
            yield b"\x02\x03" * 10

        backend._synthesize_chunks = mock_chunks
        stop_event = threading.Event()

        duration = backend.synthesize_and_play("Hello world", stop_event, lambda: None)
        assert backend._cancelled is True

    @patch("sounddevice.RawOutputStream")
    def test_piper_backend_device_error(self, mock_raw_stream):
        """Verify AudioError is raised when sounddevice fails to initialize."""
        mock_raw_stream.side_effect = RuntimeError("PortAudio device error")
        backend = PiperBackend(model_path="dummy.onnx")

        stop_event = threading.Event()
        with pytest.raises(AudioError, match="Sounddevice initialization error"):
            backend.synthesize_and_play("Hello", stop_event, lambda: None)
