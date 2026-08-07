"""
Campus Helpdesk Robot – Phase 3: Text-to-Speech (TTS) Service
==============================================================

Module: campus_helpdesk.services.tts_service
File:   src/campus_helpdesk/services/tts_service.py
Version: 1.2  (TTS Streaming + Barge-In + Multilingual)

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
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from campus_helpdesk.application.exceptions import AudioError
from campus_helpdesk.interaction.event_bus import EventBus, SubscriptionHandle
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    EventEnvelope,
    EventType,
    TTSPayload,
)

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
    """Offline TTS backend powered by Piper ONNX / binary CLI.

    Supports multiple language voices via VOICE_MAP. Voice models are loaded
    lazily and cached so subsequent sentences in the same language do not
    incur a reload penalty.
    """

    # Maps ISO-639-1 language codes → Piper model base names.
    # Extend this map to support additional languages without code changes.
    VOICE_MAP: dict[str, str] = {
        "en": "en_US-lessac-medium",
        "en_US": "en_US-lessac-medium",
        "hi": "hi_IN-pratham-medium",
        "hi_IN": "hi_IN-pratham-medium",
        # Kannada: no official Piper model — falls back to default voice.
    }

    def __init__(
        self,
        model_path: str = "en_US-lessac-medium.onnx",
        config_path: str | None = None,
        output_device: int | None = None,
        speed: float = 1.0,
        volume: float = 1.0,
    ) -> None:
        self._model_path = model_path
        self._config_path = config_path or (f"{model_path}.json" if not model_path.endswith(".json") else model_path)
        self._speed = speed
        self._volume = volume
        self._voice: Any = None
        self._sample_rate = 22050
        self._cancel_lock = threading.Lock()
        self._cancelled = False

        # Multi-voice cache: lang_code/model_name -> loaded PiperVoice
        self._voice_cache: dict[str, Any] = {}

        # Output speaker device with settings fallback & auto-detection
        self._output_device = output_device
        if self._output_device is None:
            try:
                from campus_helpdesk.config.settings import get_settings
                self._output_device = get_settings().speaker_device_index
            except (ImportError, AttributeError, KeyError):
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
            except (sd.PortAudioError, AttributeError, ValueError, OSError) as e:
                logger.warning("TTS: Could not auto-detect default output audio device: %s", e)

    def load_model(self) -> float:
        t0 = time.perf_counter()
        logger.info("Loading Piper model from %s...", self._model_path)

        if self._output_device is not None:
            try:
                import sounddevice as sd
                dev_info = sd.query_devices(self._output_device)
                logger.info("TTS Selected Speaker Index %d: %s", self._output_device, dev_info.get("name", "Unknown"))
            except (sd.PortAudioError, AttributeError, ValueError, OSError) as e:
                logger.info("TTS Selected Speaker Index %d (query failed: %s)", self._output_device, e)
        else:
            logger.warning("TTS: No speaker device selected or available.")

        loaded = False
        try:
            from piper.voice import PiperVoice
            voice = PiperVoice.load(self._model_path, config_path=self._config_path)
            if hasattr(voice, "config") and hasattr(voice.config, "sample_rate"):
                self._sample_rate = voice.config.sample_rate
            self._voice = voice
            # Cache the default voice under its model path key
            self._voice_cache[self._model_path] = voice
            loaded = True
            logger.info("Piper voice loaded successfully via python-piper module.")
        except Exception as exc:
            logger.debug("Python piper module load attempt: %s", exc)

        if not loaded:
            import os
            if not os.path.exists(self._model_path):
                alt_path = os.path.join("data", "piper", os.path.basename(self._model_path))
                if os.path.exists(alt_path):
                    self._model_path = alt_path
                    self._config_path = f"{alt_path}.json"
                else:
                    err_msg = f"Piper model file not found at {self._model_path}"
                    logger.error("TTS load failure: %s", err_msg)
                    raise AudioError(err_msg)

            if os.path.exists(self._config_path):
                try:
                    import json
                    with open(self._config_path, encoding="utf-8") as f:
                        cfg = json.load(f)
                        self._sample_rate = cfg.get("audio", {}).get("sample_rate", 22050)
                except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as json_err:
                    logger.debug("Could not parse config JSON for sample_rate: %s", json_err)

            self._voice = "CLI_SUBPROCESS"
            logger.info("Piper model path verified for subprocess execution.")

        logger.info("Warming up Piper TTS model...")
        try:
            for _ in self._synthesize_chunks("."):
                pass
            logger.info("Piper TTS model warmed up successfully.")
        except Exception as e:
            logger.warning("Failed to warm up Piper TTS model: %s", e)

        elapsed = time.perf_counter() - t0
        return elapsed

    def _load_voice_for_language(self, language: str) -> Any:
        """Lazily load and cache a Piper voice for the given language code.

        Falls back to the default loaded voice if the language is not in
        VOICE_MAP or the model file is missing.
        """
        lang_key = language.lower()
        # Check voice cache first
        if lang_key in self._voice_cache:
            return self._voice_cache[lang_key]

        model_name = self.VOICE_MAP.get(lang_key)
        if model_name is None:
            logger.info(
                "TTS: No Piper voice mapped for language %r. Using default voice.",
                language,
            )
            return self._voice  # Default voice

        # Try loading the model from the data/piper directory
        import os
        model_path = os.path.join("data", "piper", f"{model_name}.onnx")
        config_path = f"{model_path}.json"

        if not os.path.exists(model_path):
            logger.warning(
                "TTS: Voice model for %r not found at %s. Using default voice.",
                language, model_path,
            )
            self._voice_cache[lang_key] = self._voice
            return self._voice

        try:
            from piper.voice import PiperVoice
            voice = PiperVoice.load(model_path, config_path=config_path)
            self._voice_cache[lang_key] = voice
            logger.info("TTS: Loaded voice for language %r: %s", language, model_name)
            return voice
        except Exception as exc:
            logger.warning("TTS: Failed to load voice for %r: %s. Using default.", language, exc)
            self._voice_cache[lang_key] = self._voice
            return self._voice

    def _synthesize_chunks(self, text: str):
        """Internal generator producing 16-bit PCM audio byte chunks."""
        if hasattr(self._voice, "synthesize_stream_raw"):
            yield from self._voice.synthesize_stream_raw(text)
        elif hasattr(self._voice, "synthesize"):
            # modern piper.voice.PiperVoice.synthesize(text) yields AudioChunk objects
            try:
                chunks = self._voice.synthesize(text)
                for chunk in chunks:
                    if hasattr(chunk, "audio_int16_bytes") and chunk.audio_int16_bytes:
                        yield chunk.audio_int16_bytes
                    elif hasattr(chunk, "audio_bytes") and chunk.audio_bytes:
                        yield chunk.audio_bytes
            except TypeError:
                # Legacy PiperVoice that expects (text, wav_file)
                import io
                import wave
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(self._sample_rate)
                    self._voice.synthesize(text, wav)
                buf.seek(0)
                with wave.open(buf, "rb") as wav:
                    chunk_frames = 1024
                    while True:
                        data = wav.readframes(chunk_frames)
                        if not data:
                            break
                        yield data
        else:
            import os
            import shutil
            import subprocess
            piper_bin = shutil.which("piper") or "piper"
            cmd = [
                piper_bin,
                "--model", self._model_path,
                "--output-raw",
            ]
            if self._config_path and os.path.exists(self._config_path):
                cmd.extend(["--config", self._config_path])

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(text.encode("utf-8"))
                proc.stdin.close()

                chunk_size = 2048
                while True:
                    chunk = proc.stdout.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                proc.wait()
            except Exception as sub_err:
                logger.error("Piper subprocess execution error: %s", sub_err, exc_info=True)
                raise AudioError(f"Piper execution failed: {sub_err}") from sub_err

    def synthesize_and_play(
        self,
        text: str,
        stop_event: threading.Event,
        on_start_callback: Any,
        language: str = "en",
    ) -> float:
        """Synthesize text and stream audio to the speaker.

        Parameters
        ----------
        language:
            ISO 639-1 language code used to select the appropriate Piper
            voice model. If no matching model is found, falls back to the
            default loaded voice.
        """
        with self._cancel_lock:
            self._cancelled = False

        if not text or not text.strip():
            return 0.0

        t_start = time.perf_counter()

        # Select voice for language (lazy-load if needed)
        active_voice = self._load_voice_for_language(language)

        try:
            import sounddevice as sd
            stream = sd.RawOutputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                device=self._output_device,
            )
        except Exception as sd_err:
            logger.error("TTS sounddevice RawOutputStream initialization failed: %s", sd_err, exc_info=True)
            raise AudioError(f"Sounddevice initialization error: {sd_err}") from sd_err

        first_chunk = True
        try:
            with stream:
                stream.start()
                # Use language-selected voice for chunk generation
                _orig_voice = self._voice
                if active_voice is not None and active_voice is not self._voice:
                    self._voice = active_voice
                try:
                    for chunk in self._synthesize_chunks(text):
                        if stop_event.is_set() or self._cancelled:
                            logger.info("TTS playback cancelled mid-stream.")
                            break
                        if first_chunk:
                            tts_start_time = time.perf_counter()
                            logger.info("[LATENCY-PROFILER] TTS start: %.2f ms", (tts_start_time - t_start) * 1000)
                            on_start_callback()
                            first_chunk = False
                        try:
                            stream.write(chunk)
                        except Exception as write_err:
                            logger.warning("TTS sounddevice chunk write warning: %s", write_err)
                            break
                finally:
                    self._voice = _orig_voice  # Restore default voice reference
        except AudioError:
            raise
        except Exception as play_err:
            logger.warning("TTS playback stream warning: %s", play_err)

        elapsed = time.perf_counter() - t_start
        logger.info("[LATENCY-PROFILER] TTS completion: %.2f ms", elapsed * 1000)
        return elapsed

    def cancel(self) -> None:
        with self._cancel_lock:
            self._cancelled = True

    @property
    def voice_name(self) -> str:
        import os
        return f"piper:{os.path.basename(self._model_path)}"

    @property
    def sample_rate(self) -> int:
        return self._sample_rate


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
        language: str = "en",
    ) -> float:
        """Mock synthesis: simulates per-word duration, respects stop_event.

        The ``language`` parameter is accepted but ignored in the mock —
        it exists so the mock satisfies the same interface as PiperBackend.
        """
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
    """Consumes answers, streams sentence-by-sentence TTS playback, and publishes
    TTS lifecycle events.

    **Streaming behaviour**: When an ANSWER_READY event arrives, the answer text
    is split into individual sentences. Each sentence is synthesised and played
    in sequence. This means the first sentence begins playing almost immediately
    (200–400ms after ANSWER_READY) while subsequent sentences are generated
    concurrently.

    **Barge-in**: Calling ``interrupt()`` (e.g. from InteractionManager when
    a VOICE_STARTED event fires during SPEAKING) immediately stops the current
    sentence and drains any remaining queued sentences for the current answer.

    Parameters
    ----------
    event_bus:
        Central Event Bus instance.
    backend:
        Implementation of BaseSpeechBackend. Defaults to MockSpeechBackend.
    inter_sentence_pause_ms:
        Silence gap inserted between consecutive sentences in milliseconds.
        Default: 150ms. Set to 0 to disable.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: BaseSpeechBackend | None = None,
        inter_sentence_pause_ms: int = 150,
        name: str = "tts_service",
    ) -> None:
        self._bus = event_bus
        self._backend = backend or MockSpeechBackend()
        self._inter_sentence_pause_ms = inter_sentence_pause_ms
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue()
        self._running = False
        self._stop_event = threading.Event()

        # Interruption/preemption tracking
        self._preempt_event = threading.Event()
        # Generation counter: incremented on each interrupt(). The active playback
        # loop captures its generation at start and checks it before each sentence
        # to detect whether it has been superseded by a newer answer.
        self._interrupt_generation: int = 0
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Diagnostics & Metrics
        self._model_load_time = 0.0
        self._requests_processed = 0
        self._sentences_spoken = 0
        self._total_playback_ms = 0.0
        self._total_synthesis_ms = 0.0
        self._failures = 0
        self._start_time: float | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Preloads model weights.

        If the backend is blocked by SAC or model files are missing, logs a
        warning and marks TTS as degraded.  Does NOT raise so the rest of the
        pipeline (camera, vision, VAD, LLM) can still start.
        """
        with self._lock:
            try:
                self._model_load_time = self._backend.load_model()
            except Exception as exc:
                logger.warning(
                    "TTSService: model load failed (%s). "
                    "TTS will be disabled; text responses still display in GUI.",
                    exc,
                )
                self._model_load_time = -1.0  # sentinel: attempted but failed

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
        """Preempt and cancel active speech playback immediately.

        Sets the preempt event AND increments the interrupt generation counter.
        The active playback loop captures its generation at start; when it
        checks and finds the generation has advanced, it exits immediately
        without playing any remaining queued sentences.
        """
        with self._lock:
            self._preempt_event.set()
            self._interrupt_generation += 1
            self._backend.cancel()
            logger.info("TTSService: Active speech playback interrupted (gen=%d).", self._interrupt_generation)

    # ─────────────────────────────────────────────────────────────────────────
    # Sentence Splitting Utility
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def split_into_sentences(text: str) -> list[str]:
        """Split answer text into individual sentences for streaming playback.

        Handles:
        - Standard English punctuation: ``.``, ``?``, ``!``
        - Hindi/Devanagari danda: ``\u0964`` (।)
        - Double danda: ``\u0965`` (॥)
        - Newlines (treated as sentence boundaries)
        - Avoids splitting on common abbreviations (Mr., Dr., etc.)
        - Preserves trailing punctuation with each sentence.

        Returns
        -------
        list[str]
            Non-empty sentences. If the text contains no boundary, returns
            the entire text as a single-element list.
        """
        if not text or not text.strip():
            return []

        # Boundary pattern: sentence-ending punctuation followed by
        # whitespace or end-of-string. The lookbehind avoids splitting
        # common title abbreviations (Mr., Dr., etc.).
        SENTENCE_BOUNDARY = re.compile(
            r'(?<![A-Z][a-z])(?<![A-Z]{2})(?<=[.?!\u0964\u0965])(?=\s|$)'
            r'|(?<=\n)',
            re.UNICODE,
        )

        # Split on sentence boundaries, keeping the delimiter with the left part
        parts = SENTENCE_BOUNDARY.split(text)
        sentences = [s.strip() for s in parts if s and s.strip()]

        # Merge very short fragments (< 3 chars) with the preceding sentence
        merged: list[str] = []
        for s in sentences:
            if merged and len(s) < 3:
                merged[-1] = merged[-1] + " " + s
            else:
                merged.append(s)

        return merged if merged else [text.strip()]

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
        """Stream an ANSWER_READY event as sentence-by-sentence TTS playback.

        Steps
        -----
        1. Validate payload.
        2. Split answer text into sentences.
        3. Capture current interrupt generation.
        4. For each sentence:
           a. Check if generation has advanced (barge-in/preempt) — exit if so.
           b. Clear preempt event at the start of each sentence.
           c. Synthesize and play the sentence (blocking per-sentence).
           d. Publish TTS_STARTED on the first audio callback.
           e. Apply inter-sentence pause (if not interrupted).
        5. Publish TTS_COMPLETED or TTS_INTERRUPTED depending on outcome.
        """
        payload = event.payload
        if not isinstance(payload, AnswerPayload) or not payload.answer or not payload.answer.strip():
            logger.warning("TTSService: Received invalid or empty answer payload.")
            self._publish_error("InvalidAnswerError", "Answer text is blank or missing.", event)
            return

        full_text = payload.answer.strip()
        language = getattr(payload, "language", "en")
        session_id = event.session_id or "default"

        # Split into sentences for streaming playback
        sentences = self.split_into_sentences(full_text)
        if not sentences:
            self._publish_error("InvalidAnswerError", "Answer split into zero sentences.", event)
            return

        # Capture current generation so we can detect barge-in mid-answer
        with self._lock:
            my_generation = self._interrupt_generation

        # Reset preemption trigger at the start of this answer
        self._preempt_event.clear()

        total_playback_ms = 0
        interrupted = False
        first_sentence_started = False
        t_answer_start = time.perf_counter()

        logger.info(
            "TTSService: Playing %d sentence(s) in language=%r: %r...",
            len(sentences), language, full_text[:60],
        )

        for i, sentence in enumerate(sentences):
            # Check if a barge-in or new answer has superseded this one
            with self._lock:
                current_gen = self._interrupt_generation
            if current_gen != my_generation or self._preempt_event.is_set():
                logger.info(
                    "TTSService: Sentence %d/%d skipped — superseded (gen %d -> %d).",
                    i + 1, len(sentences), my_generation, current_gen,
                )
                interrupted = True
                break

            # Clear preempt for this sentence's playback
            self._preempt_event.clear()

            sentence_text = sentence.strip()
            if not sentence_text:
                continue

            # Closure: publishes TTS_STARTED on first audio chunk of the full answer
            def make_on_start(sent_text: str = sentence_text, first: bool = (i == 0)) -> Any:
                def on_start() -> None:
                    nonlocal first_sentence_started
                    if first and not first_sentence_started:
                        first_sentence_started = True
                        logger.info("TTSService: First sentence playback started.")
                        self._bus.publish(
                            EventEnvelope.create(
                                event_type=EventType.TTS_STARTED,
                                source=self._name,
                                payload=TTSPayload(
                                    text=full_text,
                                    voice_model=self._backend.voice_name,
                                    duration_ms=0,
                                ),
                                session_id=session_id,
                                correlation_id=event.event_id,
                            )
                        )
                return on_start

            try:
                playback_sec = self._backend.synthesize_and_play(
                    text=sentence_text,
                    stop_event=self._preempt_event,
                    on_start_callback=make_on_start(),
                    language=language,
                )
                sent_ms = playback_sec * 1000
                total_playback_ms += sent_ms

                with self._lock:
                    self._sentences_spoken += 1
                    self._total_playback_ms += sent_ms

            except Exception as exc:
                with self._lock:
                    self._failures += 1
                logger.error(
                    "TTSService: Synthesis failure on sentence %d %r: %s",
                    i + 1, sentence_text[:40], exc, exc_info=True,
                )
                self._publish_error("TTSSynthesisError", f"TTS synthesis/playback failed: {exc}", event)
                interrupted = True
                break

            # Check interruption after each sentence
            with self._lock:
                post_gen = self._interrupt_generation
            if post_gen != my_generation or self._preempt_event.is_set():
                interrupted = True
                break

            # Inter-sentence pause (skip after last sentence or if interrupted)
            if i < len(sentences) - 1 and self._inter_sentence_pause_ms > 0:
                pause_sec = self._inter_sentence_pause_ms / 1000.0
                # Honour preempt during pause via short polling
                t_pause = time.perf_counter()
                while time.perf_counter() - t_pause < pause_sec:
                    if self._preempt_event.is_set():
                        interrupted = True
                        break
                    time.sleep(0.01)
                if interrupted:
                    break

        t_answer_end = time.perf_counter()
        total_answer_ms = int((t_answer_end - t_answer_start) * 1000)
        latency_ms = total_answer_ms - int(total_playback_ms)

        with self._lock:
            self._requests_processed += 1
            self._total_synthesis_ms += latency_ms

        # Ensure TTS_STARTED was published even if first sentence was empty
        if not first_sentence_started:
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.TTS_STARTED,
                    source=self._name,
                    payload=TTSPayload(
                        text=full_text,
                        voice_model=self._backend.voice_name,
                        duration_ms=0,
                    ),
                    session_id=session_id,
                    correlation_id=event.event_id,
                )
            )

        if interrupted:
            logger.info("TTSService: Answer interrupted after %dms.", total_answer_ms)
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.TTS_INTERRUPTED,
                    source=self._name,
                    payload=TTSPayload(
                        text=full_text,
                        voice_model=self._backend.voice_name,
                        duration_ms=int(total_playback_ms),
                        interrupted_at_ms=int(total_playback_ms),
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
                        text=full_text,
                        voice_model=self._backend.voice_name,
                        duration_ms=int(total_playback_ms),
                        interrupted_at_ms=None,
                    ),
                    session_id=session_id,
                    correlation_id=event.event_id,
                )
            )

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
                self._total_playback_ms / self._sentences_spoken if self._sentences_spoken > 0 else 0.0
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
                "sentences_spoken": self._sentences_spoken,
                "worker_status": "running" if (self._worker and self._worker.is_alive()) else "stopped",
                "failures": self._failures,
                "uptime_seconds": round(uptime_sec, 3),
                "inter_sentence_pause_ms": self._inter_sentence_pause_ms,
                "interrupt_generation": self._interrupt_generation,
            }
