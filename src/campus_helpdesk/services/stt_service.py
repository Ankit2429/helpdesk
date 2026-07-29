"""
Campus Helpdesk Robot – Phase 3: Speech-to-Text (STT) Service
==============================================================

Module: campus_helpdesk.services.stt_service
File:   src/campus_helpdesk/services/stt_service.py
Version: 1.0

This service manages the conversion of completed speech audio files into text.
It consumes ``VOICE_STOPPED`` events containing the file path to a recorded WAV
segment, runs transcription via a decoupled backend interface, and publishes
``TRANSCRIPT_FINAL`` events containing the text.

Thread Model
------------
*  **Worker Thread** – dedicated loop (``STTService-worker``) pulling audio
   transcription requests from an internal FIFO queue (``queue.Queue``). This
   ensures incoming requests do not interrupt active transcriptions.
*  **Thread Safety** – all lifecycle, metric updates, and diagnostics queries
   are protected by a reentrant lock (``threading.RLock``).
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
    EventEnvelope,
    EventType,
    TranscriptPayload,
    VoicePayload,
)

from campus_helpdesk.application.exceptions import AudioError
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backend Abstraction
# ---------------------------------------------------------------------------


class BaseTranscriptionBackend(ABC):
    """Abstract base class for transcription engines (Whisper, Mock, etc.)."""

    @abstractmethod
    def load_model(self) -> float:
        """Preload the transcription model during initialization.

        Returns
        -------
        load_time_seconds:
            Duration taken to load the model.
        """
        pass

    @abstractmethod
    def transcribe(self, audio_path: str) -> tuple[str, str, float]:
        """Transcribe the given audio file.

        Parameters
        ----------
        audio_path:
            Local file path to the audio WAV segment.

        Returns
        -------
        text:
            Recognized transcription text.
        language:
            Detected language code (e.g. "en").
        confidence:
            Confidence score in range [0.0, 1.0].
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name/size of the transcription model currently loaded."""
        pass


class FasterWhisperBackend(BaseTranscriptionBackend):
    """Speech-to-text backend powered by faster-whisper (ctranslate2)."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._cpu_threads = cpu_threads
        self._model: Any = None

    def load_model(self) -> float:
        t0 = time.perf_counter()
        logger.info(
            "Loading Faster-Whisper model %r on %s (%s)...",
            self._model_size,
            self._device,
            self._compute_type,
        )
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                cpu_threads=self._cpu_threads,
            )
        except ImportError as exc:
            logger.error("Failed to import faster-whisper: %s", exc)
            raise RuntimeError("faster-whisper is not installed in the environment") from exc

        elapsed = time.perf_counter() - t0
        logger.info("Faster-Whisper model loaded in %.2fs.", elapsed)
        return elapsed

    def transcribe(self, audio_path: str) -> tuple[str, str, float]:
        if self._model is None:
            raise RuntimeError("Faster-Whisper model is not preloaded.")

        # beam_size=5 (default)
        segments, info = self._model.transcribe(audio_path, beam_size=5)
        
        # Pull text from iterator
        text_segments = [s.text for s in segments]
        text = " ".join(text_segments).strip()
        confidence = round(float(info.language_probability), 4)
        return text, info.language, confidence

    @property
    def model_name(self) -> str:
        return f"faster-whisper:{self._model_size}:{self._device}:{self._compute_type}"


class MockTranscriptionBackend(BaseTranscriptionBackend):
    """Mock backend returning predefined transcripts for test validation."""

    def __init__(
        self,
        dummy_text: str = "where is the central library",
        model_name: str = "mock-whisper-tiny",
    ) -> None:
        self._dummy_text = dummy_text
        self._model_name = model_name
        self._load_time = 0.05

    def load_model(self) -> float:
        time.sleep(self._load_time)
        return self._load_time

    def transcribe(self, audio_path: str) -> tuple[str, str, float]:
        # Simulate small filesystem read delay
        time.sleep(0.01)
        
        # Check for empty file simulation
        if "empty" in audio_path.lower():
            return "", "en", 0.0
        # Check for corrupt simulation
        if "corrupt" in audio_path.lower():
            raise IOError("Corrupt audio file header")

        return self._dummy_text, "en", 0.96

    @property
    def model_name(self) -> str:
        return self._model_name


# ---------------------------------------------------------------------------
# STT Service
# ---------------------------------------------------------------------------


class STTService:
    """Manages the transcription queue and processes WAV audio segments.

    Parameters
    ----------
    event_bus:
        The Event Bus instance to publish events to.
    backend:
        Implementation of BaseTranscriptionBackend. Defaults to FasterWhisper.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: BaseTranscriptionBackend | None = None,
        name: str = "stt_service",
    ) -> None:
        self._bus = event_bus
        self._backend = backend or MockTranscriptionBackend()
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue()
        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Diagnostics & Metrics
        self._model_load_time = 0.0
        self._files_processed = 0
        self._total_transcribe_ms = 0.0
        self._total_confidence = 0.0
        self._avg_confidence = 0.0
        self._start_time: float | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Preloads the underlying transcription model."""
        with self._lock:
            self._model_load_time = self._backend.load_model()

    def start(self) -> None:
        """Start the worker thread and subscribe to VOICE_STOPPED events."""
        with self._lock:
            if self._running:
                return

            if self._model_load_time == 0.0:
                self.initialize()

            self._running = True
            self._stop_event.clear()
            self._start_time = time.perf_counter()

            # Subscribe to VOICE_STOPPED
            self._sub_handle = self._bus.subscribe(
                self._enqueue_request,
                event_types=EventType.VOICE_STOPPED,
                source=self._name,
            )

            # Start Worker Thread
            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self._name}-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info("STTService started with backend: %s", self._backend.model_name)

    def stop(self) -> None:
        """Stop worker thread and unsubscribe from the event bus."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

            if self._sub_handle:
                self._bus.unsubscribe(self._sub_handle)
                self._sub_handle = None

        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)

        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        logger.info("STTService stopped.")

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    # ─────────────────────────────────────────────────────────────────────────
    # Queue Ingestion & Worker Thread
    # ─────────────────────────────────────────────────────────────────────────

    def _enqueue_request(self, event: EventEnvelope) -> None:
        """Enqueues incoming transcription requests."""
        if not self.is_running():
            return
        self._queue.put(event)

    def _worker_loop(self) -> None:
        """FIFO worker loop pulling WAV paths and running transcription."""
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._process_request(event)
            except Exception as exc:
    logger.error("STTService error: %s", exc)
    raise AudioError(str(exc))
            finally:
                self._queue.task_done()

    def _process_request(self, event: EventEnvelope) -> None:
        payload = event.payload
        if not isinstance(payload, VoicePayload) or not payload.audio_segment_path:
            return

        wav_path = payload.audio_segment_path
        t_start = time.perf_counter()

        try:
            # Execute backend transcription
            text, lang, confidence = self._backend.transcribe(wav_path)
            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000

            with self._lock:
                self._files_processed += 1
                self._total_transcribe_ms += latency_ms
                self._total_confidence += confidence
                self._avg_confidence = self._total_confidence / self._files_processed

            # Publish TRANSCRIPT_FINAL
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.TRANSCRIPT_FINAL,
                    source=self._name,
                    payload=TranscriptPayload(
                        text=text,
                        is_final=True,
                        language=lang,
                        confidence=confidence,
                        duration_ms=payload.duration_ms,
                        audio_chunk_id=payload.audio_chunk_id,
                    ),
                    session_id=event.session_id,
                    correlation_id=event.event_id,
                    metadata={
                        "transcription_latency_ms": str(round(latency_ms, 2)),
                        "model_name": self._backend.model_name,
                    },
                )
            )

        except Exception as exc:
            logger.error("STT transcription failure on file %s: %s", wav_path, exc)
            raise AudioError(str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status APIs
    # ─────────────────────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            avg_latency = (
                self._total_transcribe_ms / self._files_processed if self._files_processed > 0 else 0.0
            )
            uptime_sec = time.perf_counter() - self._start_time if self._start_time else 0.0

            return {
                "current_model": self._backend.model_name,
                "model_load_time_seconds": round(self._model_load_time, 3),
                "average_transcription_latency_ms": round(avg_latency, 3),
                "files_processed": self._files_processed,
                "queue_depth": self._queue.qsize(),
                "worker_status": "running" if (self._worker and self._worker.is_alive()) else "stopped",
                "average_confidence": round(self._avg_confidence, 3),
                "uptime_seconds": round(uptime_sec, 3),
            }
