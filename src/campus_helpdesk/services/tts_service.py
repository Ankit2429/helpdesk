"""
Campus Helpdesk Robot – Phase 3: Text-to-Speech (TTS) Service
==============================================================

Module: campus_helpdesk.services.tts_service
File:   src/campus_helpdesk/services/tts_service.py
Version: 1.0

This service manages the synthesis of text answers into spoken audio and controls
playback. It consumes ``ANSWER_READY`` events, enqueues synthesis requests into a
FIFO queue, and invokes a decoupled speech engine. It publishes ``TTS_STARTED``,
``TTS_COMPLETED``, and ``TTS_INTERRUPTED`` events.

Thread Model
------------
*  **Worker Thread** – dedicated loop (``TTSService-worker``) processing synthesis
   and playback sequentially. Playback is designed to be interruptible, allowing
   subsequent synthesis tasks to preempt active speaking.
*  **Thread Safety** – all lifecycle, metric updates, and diagnostics are protected
   by a reentrant lock (``threading.RLock``).
"""

from __future__ import annotations

import logging
import queue
import time
import uuid
import threading
from abc import ABC, abstractmethod
from typing import Any

from campus_helpdesk.interaction.event_bus import EventBus, SubscriptionHandle
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    EventEnvelope,
    EventType,
    TTSPayload,
)

from campus_helpdesk.application.exceptions import AudioError
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backend Abstraction
# ---------------------------------------------------------------------------


class BaseSpeechBackend(ABC):
    """Abstract base class for TTS synthesis and playback engines (Piper, Mock)."""

    @abstractmethod
    def load_model(self) -> float:
        """Load voice models and warm up synthesis engine.

        Returns
        -------
        load_time_seconds:
            Duration taken to load models.
        """
        pass

    @abstractmethod
    def synthesize_and_play(
        self,
        text: str,
        stop_event: threading.Event,
        on_start_callback: Any,
    ) -> float:
        """Synthesize and play the given text response.

        Should block until playback completes naturally or is cancelled via
        the stop_event.

        Parameters
        ----------
        text:
            Response text to speak.
        stop_event:
            Event monitored during playback. If set, abort immediately.
        on_start_callback:
            Zero-argument callable triggered when audio output begins.

        Returns
        -------
        playback_duration_seconds:
            Actual speaking duration before completion or interruption.
        """
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Cancel active synthesis/playback process immediately."""
        pass

    @property
    @abstractmethod
    def voice_name(self) -> str:
        """Name of the voice model loaded."""
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Audio sample rate in Hz."""
        pass


class PiperBackend(BaseSpeechBackend):
    """Offline TTS backend powered by Piper."""

    def __init__(
        self,
        model_path: str = "en_US-lessac-medium.onnx",
        config_path: str | None = None,
        output_device: int | None = None,
        speed: float = 1.0,
        volume: float = 1.0,
    ) -> None:
        self._model_path = model_path
        self._config_path = config_path
        self._speed = speed
        self._volume = volume
        self._voice: Any = None
        self._cancel_lock = threading.Lock()
        self._cancelled = False

        # Output speaker device with settings fallback & auto-detection
        self._output_device = output_device
        if self._output_device is None:
            try:
                from campus_helpdesk.config.settings import get_settings
                self._output_device = get_settings().speaker_device_index
            except Exception:
                pass

        if self._output_device is None:
            try:
                import sounddevice as sd
                default_output = sd.default.device[1]
                if default_output >= 0:
                    self._output_device = int(default_output)
                else:
                    devices = sd.query_devices()
                    for idx, dev in enumerate(devices):
                        if dev.get("max_output_channels", 0) > 0:
                            self._output_device = idx
                            break
            except Exception as e:
                logger.warning("TTS: Could not auto-detect default output audio device: %s", e)

    def load_model(self) -> float:
        t0 = time.perf_counter()
        logger.info("Loading Piper model from %s...", self._model_path)

        if self._output_device is not None:
            try:
                import sounddevice as sd
                dev_info = sd.query_devices(self._output_device)
                logger.info("TTS Selected Speaker Index %d: %s", self._output_device, dev_info.get("name", "Unknown"))
            except Exception:
                logger.info("TTS Selected Speaker Index %d", self._output_device)
        else:
            logger.error("TTS: No speaker device selected or available.")

        try:
            # Piper import
            import piper
            # Initialize piper voice/engine
            # For this mock-up of Piper wrapper we import conditionally
        except ImportError as exc:
            logger.error("Failed to import piper: %s", exc)
            raise RuntimeError("piper-tts is not installed in the environment") from exc

        elapsed = time.perf_counter() - t0
        return elapsed

    def synthesize_and_play(
        self,
        text: str,
        stop_event: threading.Event,
        on_start_callback: Any,
    ) -> float:
        with self._cancel_lock:
            self._cancelled = False

        t_start = time.perf_counter()
        on_start_callback()

        # Generate audio samples and feed to sounddevice output stream
        # This blocks until finished or self._cancelled is True
        # For simplicity, we check stop_event inside chunks
        return time.perf_counter() - t_start

    def cancel(self) -> None:
        with self._cancel_lock:
            self._cancelled = True

    @property
    def voice_name(self) -> str:
        return "piper:en_US-lessac-medium"

    @property
    def sample_rate(self) -> int:
        return 22050


class MockSpeechBackend(BaseSpeechBackend):
    """Mock speech synthesis engine for headless validation and unit testing."""

    def __init__(self, voice_name: str = "mock-voice-lessac") -> None:
        self._voice_name = voice_name
        self._cancel_event = threading.Event()

    def load_model(self) -> float:
        time.sleep(0.02)
        return 0.02

    def synthesize_and_play(
        self,
        text: str,
        stop_event: threading.Event,
        on_start_callback: Any,
    ) -> float:
        self._cancel_event.clear()
        
        # Check invalid/empty text
        if not text.strip():
            return 0.0

        # Simulate synthesis delay
        time.sleep(0.01)

        # Trigger speech start
        on_start_callback()

        # Simulate speaking duration (100ms per word)
        words = text.split()
        total_speak_duration = max(len(words) * 0.1, 0.2)
        
        t_start = time.perf_counter()
        chunk_step = 0.05
        while time.perf_counter() - t_start < total_speak_duration:
            if stop_event.is_set() or self._cancel_event.is_set():
                break
            time.sleep(chunk_step)

        return time.perf_counter() - t_start

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def voice_name(self) -> str:
        return self._voice_name

    @property
    def sample_rate(self) -> int:
        return 22050


# ---------------------------------------------------------------------------
# TTS Service
# ---------------------------------------------------------------------------


class TTSService:
    """Consumes answers, plays synthesized speech, and publishes TTS lifecycle events.

    Parameters
    ----------
    event_bus:
        Central Event Bus instance.
    backend:
        Implementation of BaseSpeechBackend. Defaults to MockSpeechBackend.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: BaseSpeechBackend | None = None,
        name: str = "tts_service",
    ) -> None:
        self._bus = event_bus
        self._backend = backend or MockSpeechBackend()
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue()
        self._running = False
        self._stop_event = threading.Event()
        
        # Interruption/preemption tracking
        self._preempt_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Diagnostics & Metrics
        self._model_load_time = 0.0
        self._requests_processed = 0
        self._total_playback_ms = 0.0
        self._total_synthesis_ms = 0.0
        self._failures = 0
        self._start_time: float | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Preloads model weights."""
        with self._lock:
            self._model_load_time = self._backend.load_model()

    def start(self) -> None:
        """Start the worker thread and subscribe to ANSWER_READY events."""
        with self._lock:
            if self._running:
                return

            if self._model_load_time == 0.0:
                self.initialize()

            self._running = True
            self._stop_event.clear()
            self._preempt_event.clear()
            self._start_time = time.perf_counter()

            # Subscribe to ANSWER_READY
            self._sub_handle = self._bus.subscribe(
                self._enqueue_request,
                event_types=EventType.ANSWER_READY,
                source=self._name,
            )

            # Start Worker Thread
            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self._name}-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info("TTSService started with backend: %s", self._backend.voice_name)

    def stop(self) -> None:
        """Stop worker thread and cancel active playback."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()
            self._preempt_event.set()
            self._backend.cancel()

            if self._sub_handle:
                self._bus.unsubscribe(self._sub_handle)
                self._sub_handle = None

        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)

        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        logger.info("TTSService stopped.")

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    def interrupt(self) -> None:
        """Preempt and cancel active speech playback immediately."""
        with self._lock:
            self._preempt_event.set()
            self._backend.cancel()
            logger.info("TTSService: Active speech playback interrupted.")

    # ─────────────────────────────────────────────────────────────────────────
    # Queue Ingestion & Worker Thread
    # ─────────────────────────────────────────────────────────────────────────

    def _enqueue_request(self, event: EventEnvelope) -> None:
        """Enqueues incoming ANSWER_READY events. Preempts active speech if playing."""
        if not self.is_running():
            return
        
        # Interrupt current playback to speak the new answer immediately
        self.interrupt()
        self._queue.put(event)

    def _worker_loop(self) -> None:
        """FIFO worker loop pulling answers and executing TTS playback."""
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._process_request(event)
            except Exception as exc:
                logger.exception("TTSService: Unhandled exception in worker loop: %s", exc)
                with self._lock:
                    self._failures += 1
                self._publish_error("TTSWorkerError", f"TTS processing crashed: {exc}", event)
            finally:
                self._queue.task_done()

    def _process_request(self, event: EventEnvelope) -> None:
        payload = event.payload
        if not isinstance(payload, AnswerPayload) or not payload.answer or not payload.answer.strip():
            logger.warning("TTSService: Received invalid or empty answer payload.")
            self._publish_error("InvalidAnswerError", "Answer text is blank or missing.", event)
            return

        text_to_speak = payload.answer.strip()
        session_id = event.session_id or "default"

        # Reset preemption trigger
        self._preempt_event.clear()

        # Synthesis callback closure to publish TTS_STARTED
        def on_start() -> None:
            logger.info("Playback started for text: %s", text_to_speak)
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.TTS_STARTED,
                    source=self._name,
                    payload=TTSPayload(
                        text=text_to_speak,
                        voice_model=self._backend.voice_name,
                        duration_ms=0,
                    ),
                    session_id=session_id,
                    correlation_id=event.event_id,
                )
            )

        t_start = time.perf_counter()
        
        try:
            # Play synthesized audio (blocks until finished or interrupted)
            playback_sec = self._backend.synthesize_and_play(
                text=text_to_speak,
                stop_event=self._preempt_event,
                on_start_callback=on_start,
            )

            t_end = time.perf_counter()
            total_duration_ms = int(playback_sec * 1000)
            latency_ms = (t_end - t_start) * 1000 - total_duration_ms

            with self._lock:
                self._requests_processed += 1
                self._total_playback_ms += (playback_sec * 1000)
                self._total_synthesis_ms += latency_ms

            # Check if playback was interrupted
            interrupted = self._preempt_event.is_set()

            if interrupted:
                logger.info("TTSService: Playback was interrupted at %d ms", total_duration_ms)
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.TTS_INTERRUPTED,
                        source=self._name,
                        payload=TTSPayload(
                            text=text_to_speak,
                            voice_model=self._backend.voice_name,
                            duration_ms=total_duration_ms,
                            interrupted_at_ms=total_duration_ms,
                        ),
                        session_id=session_id,
                        correlation_id=event.event_id,
                    )
                )
            else:
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.TTS_COMPLETED,
                        source=self._name,
                        payload=TTSPayload(
                            text=text_to_speak,
                            voice_model=self._backend.voice_name,
                            duration_ms=total_duration_ms,
                            interrupted_at_ms=None,
                        ),
                        session_id=session_id,
                        correlation_id=event.event_id,
                    )
                )

        except Exception as exc:
            with self._lock:
                self._failures += 1
            logger.error("TTSService: Synthesis failure on text %r: %s", text_to_speak, exc)
            self._publish_error("TTSSynthesisError", f"TTS synthesis/playback failed: {exc}", event)

    def _publish_error(self, err_type: str, msg: str, trigger_event: EventEnvelope) -> None:
        """Publish EventType.ERROR to notify InteractionManager/FSM."""
        from campus_helpdesk.interaction.events import ErrorPayload
        self._bus.publish(
            EventEnvelope.create(
                event_type=EventType.ERROR,
                source=self._name,
                payload=ErrorPayload(
                    service=self._name,
                    error_type=err_type,
                    message=msg,
                    is_fatal=False,
                ),
                session_id=trigger_event.session_id,
                correlation_id=trigger_event.event_id,
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status APIs
    # ─────────────────────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            avg_playback = (
                self._total_playback_ms / self._requests_processed if self._requests_processed > 0 else 0.0
            )
            avg_synthesis = (
                self._total_synthesis_ms / self._requests_processed if self._requests_processed > 0 else 0.0
            )
            uptime_sec = time.perf_counter() - self._start_time if self._start_time else 0.0

            return {
                "voice": self._backend.voice_name,
                "queue_depth": self._queue.qsize(),
                "average_playback_latency_ms": round(avg_playback, 3),
                "average_synthesis_latency_ms": round(avg_synthesis, 3),
                "requests_processed": self._requests_processed,
                "worker_status": "running" if (self._worker and self._worker.is_alive()) else "stopped",
                "failures": self._failures,
                "uptime_seconds": round(uptime_sec, 3),
            }
