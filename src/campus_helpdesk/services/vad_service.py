"""
Campus Helpdesk Robot – Phase 3: Voice Activity Detection (VAD) Service
=====================================================================

Module: campus_helpdesk.services.vad_service
File:   src/campus_helpdesk/services/vad_service.py
Version: 1.0

This service manages the microphone hardware lifecycle and performs real-time
voice activity detection (VAD). It streams audio chunks, runs them through the
prebuilt WebRTC VAD engine, debounces speech onset and offset thresholds to avoid
noise, and publishes ``VOICE_STARTED`` and ``VOICE_STOPPED`` events.

Thread Model
------------
*  **Audio Stream Thread** – sounddevice input callback thread. Captures raw
   PCM 16-bit audio frames and enqueues them.
*  **Worker Thread** – dedicated loop (``VADService-worker``) pulling audio
   chunks, running WebRTC VAD classification, and recording audio segment files.
*  **Thread Safety** – all state updates and diagnostics queries are guarded by
   a reentrant lock (``threading.RLock``).
"""

from __future__ import annotations

import logging
import os
import queue
import tempfile
import threading
import time
import uuid
import wave
from typing import Any

import numpy as np
import sounddevice as sd
import webrtcvad

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import EventEnvelope, EventType, VoicePayload

logger = logging.getLogger(__name__)


class VADService:
    """Production-grade VAD Service managing audio capture and speech detection.

    Parameters
    ----------
    event_bus:
        The Event Bus instance to publish events to.
    sample_rate:
        Audio sample rate in Hz. Must be 8000, 16000, 32000, or 48000.
    frame_duration_ms:
        Frame duration in milliseconds. Must be 10, 20, or 30.
    aggressiveness:
        WebRTC VAD aggressiveness mode (0, 1, 2, or 3).
    speech_frames_threshold:
        Consecutive speech frames required to trigger VOICE_STARTED.
    silence_frames_threshold:
        Consecutive silence frames required to trigger VOICE_STOPPED.
    device_index:
        Sound device input index. None selects default microphone.
    use_mock_fallback:
        If True, simulates microphone capture if hardware opens fail.
    """

    def __init__(
        self,
        event_bus: EventBus,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
        speech_frames_threshold: int = 5,
        silence_frames_threshold: int = 15,
        device_index: int | None = None,
        use_mock_fallback: bool = True,
        name: str = "vad_service",
    ) -> None:
        self._bus = event_bus
        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._aggressiveness = aggressiveness
        self._speech_frames_threshold = speech_frames_threshold
        self._silence_frames_threshold = silence_frames_threshold
        self._device_index = device_index
        self._use_mock_fallback = use_mock_fallback
        self._name = name

        # Validate VAD Parameters
        if sample_rate not in {8000, 16000, 32000, 48000}:
            raise ValueError("VAD sample rate must be 8000, 16000, 32000, or 48000 Hz")
        if frame_duration_ms not in {10, 20, 30}:
            raise ValueError("VAD frame duration must be 10, 20, or 30 ms")
        if not 0 <= aggressiveness <= 3:
            raise ValueError("VAD aggressiveness mode must be between 0 and 3")

        # Frame parameters
        self._samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        self._bytes_per_sample = 2  # Int16 mono PCM
        self._frame_bytes_size = self._samples_per_frame * self._bytes_per_sample

        self._lock = threading.RLock()
        self._vad = webrtcvad.Vad(self._aggressiveness)
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        
        self._running = False
        self._stream: sd.InputStream | None = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Mock microphone state
        self._is_mock = False
        self._mock_thread: threading.Thread | None = None

        # Perception State
        self._is_speaking = False
        self._consecutive_speech = 0
        self._consecutive_silence = 0
        self._active_audio_chunk_id: str | None = None
        self._audio_frames_buffer: list[bytes] = []

        # Diagnostics & Metrics
        self._frames_processed = 0
        self._dropped_frames = 0
        self._total_process_ms = 0.0
        self._speech_duration_sec = 0.0
        self._silence_duration_sec = 0.0
        self._microphone_connected = False
        self._start_time: float | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialize and start microphone stream and processing threads."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._stop_event.clear()
            self._start_time = time.perf_counter()

            # Empty queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

            # Try initializing SoundDevice input stream
            try:
                self._stream = sd.InputStream(
                    device=self._device_index,
                    channels=1,
                    samplerate=self._sample_rate,
                    dtype="int16",
                    blocksize=self._samples_per_frame,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._microphone_connected = True
                self._is_mock = False
                logger.info("Microphone started. Streaming at %d Hz.", self._sample_rate)
            except Exception as exc:
                logger.warning("Failed to start sounddevice microphone: %s", exc)
                self._stream = None
                self._microphone_connected = False

                if self._use_mock_fallback:
                    self._is_mock = True
                    self._microphone_connected = True
                    self._mock_thread = threading.Thread(
                        target=self._mock_mic_loop,
                        name=f"{self._name}-mock-mic",
                        daemon=True,
                    )
                    self._mock_thread.start()
                    logger.info("VAD mock microphone fallback running.")
                else:
                    self._running = False
                    raise RuntimeError("Failed to initialize VAD audio hardware stream") from exc

            # Start VAD Processing Thread
            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self._name}-worker",
                daemon=True,
            )
            self._worker.start()

            # Publish MICROPHONE_STARTED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.MICROPHONE_STARTED,
                    source=self._name,
                    payload=VoicePayload(
                        audio_chunk_id=str(uuid.uuid4()),
                        sample_rate=self._sample_rate,
                        duration_ms=0,
                    ),
                )
            )

    def stop(self) -> None:
        """Stop VAD worker threads and close microphone streams."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

        # Stop hardware stream
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)

        if self._mock_thread and self._mock_thread.is_alive():
            self._mock_thread.join(timeout=2.0)

        with self._lock:
            self._microphone_connected = False
            self._is_speaking = False
            self._audio_frames_buffer.clear()

            # Publish MICROPHONE_STOPPED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.MICROPHONE_STOPPED,
                    source=self._name,
                    payload=VoicePayload(
                        audio_chunk_id=self._active_audio_chunk_id or str(uuid.uuid4()),
                        sample_rate=self._sample_rate,
                        duration_ms=0,
                    ),
                )
            )
            logger.info("VADService stopped.")

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    def is_speaking(self) -> bool:
        """Query active speaking status."""
        with self._lock:
            return self._is_speaking

    # ─────────────────────────────────────────────────────────────────────────
    # Audio Callbacks & Mock Ingestion
    # ─────────────────────────────────────────────────────────────────────────

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: Any, status: Any
    ) -> None:
        """Sounddevice callback running on internal audio thread."""
        if not self._running:
            return

        if status:
            logger.warning("VAD stream warning status: %s", status)

        # Convert numpy array (int16 mono) to raw PCM bytes
        raw_bytes = indata.tobytes()
        try:
            self._queue.put_nowait(raw_bytes)
        except queue.Full:
            with self._lock:
                self._dropped_frames += 1

    def _mock_mic_loop(self) -> None:
        """Generates periodic mock speech/silence audio frames for simulation."""
        frame_sec = self._frame_duration_ms / 1000.0
        sine_phase = 0.0

        while not self._stop_event.is_set():
            t_start = time.perf_counter()

            # Simulate 2.5 seconds speaking, 3.5 seconds silence pattern
            cycle_time = time.time() % 6.0
            speaking = cycle_time < 2.5

            if speaking:
                # Generate a mock speech frame: sine wave at 400Hz mixed with random noise
                t = np.arange(self._samples_per_frame) / self._sample_rate
                # Ensure phase continuity
                phase_inc = 2 * np.pi * 400.0 * frame_sec
                # Construct wave
                vals = np.sin(2 * np.pi * 400.0 * t + sine_phase) * 12000
                vals += np.random.normal(0, 1500, self._samples_per_frame)
                sine_phase = (sine_phase + phase_inc) % (2 * np.pi)
                data = vals.astype(np.int16).tobytes()
            else:
                # Silent frame: low background noise
                vals = np.random.normal(0, 50, self._samples_per_frame)
                data = vals.astype(np.int16).tobytes()

            try:
                self._queue.put_nowait(data)
            except queue.Full:
                with self._lock:
                    self._dropped_frames += 1

            # Sleep to match real-time
            elapsed = time.perf_counter() - t_start
            sleep_time = frame_sec - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ─────────────────────────────────────────────────────────────────────────
    # VAD Processing Thread
    # ─────────────────────────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        """VAD worker thread reading audio bytes and classification."""
        while not self._stop_event.is_set():
            try:
                frame_bytes = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            t_start = time.perf_counter()

            # Run WebRTC VAD classification
            is_speech = self._classify_frame(frame_bytes)

            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000

            with self._lock:
                self._frames_processed += 1
                self._total_process_ms += latency_ms

                # Record stats
                dur = self._frame_duration_ms / 1000.0
                if is_speech:
                    self._speech_duration_sec += dur
                else:
                    self._silence_duration_sec += dur

                self._evaluate_speech_transitions(is_speech, frame_bytes)

    def _classify_frame(self, frame_bytes: bytes) -> bool:
        """Classify if the frame contains active speech using webrtcvad."""
        # Frame bytes size must match sample count exactly
        if len(frame_bytes) != self._frame_bytes_size:
            return False

        try:
            return self._vad.is_speech(frame_bytes, self._sample_rate)
        except Exception as exc:
            logger.error("WebRTC VAD error: %s", exc)
            return False

    def _evaluate_speech_transitions(self, is_speech: bool, frame_bytes: bytes) -> None:
        """Evaluate hits/misses thresholds and publish VAD started/stopped events."""
        if is_speech:
            self._consecutive_speech += 1
            self._consecutive_silence = 0
            
            # If speaking, append raw frame bytes to active buffer
            if self._is_speaking or self._consecutive_speech >= self._speech_duration_frames():
                self._audio_frames_buffer.append(frame_bytes)
        else:
            self._consecutive_silence += 1
            self._consecutive_speech = 0
            
            # Continue buffering speech tail to avoid clipping word endings
            if self._is_speaking:
                self._audio_frames_buffer.append(frame_bytes)

        # 1. State change: Quiet -> Speaking
        if not self._is_speaking and self._consecutive_speech >= self._speech_frames_threshold:
            self._is_speaking = True
            self._active_audio_chunk_id = str(uuid.uuid4())
            logger.info("VAD: Voice Started (chunk_id=%s)", self._active_audio_chunk_id[:8])

            # Publish VOICE_STARTED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STARTED,
                    source=self._name,
                    payload=VoicePayload(
                        audio_chunk_id=self._active_audio_chunk_id,
                        sample_rate=self._sample_rate,
                        duration_ms=0,
                    ),
                )
            )

        # 2. State change: Speaking -> Quiet
        elif self._is_speaking and self._consecutive_silence >= self._silence_frames_threshold:
            self._is_speaking = False
            chunk_id = self._active_audio_chunk_id
            
            # Write buffered audio frames to temporary WAV file
            wav_path = self._write_wav_segment()
            duration_ms = len(self._audio_frames_buffer) * self._frame_duration_ms
            
            logger.info(
                "VAD: Voice Stopped (chunk_id=%s, duration=%dms, file=%s)",
                chunk_id[:8],
                duration_ms,
                os.path.basename(wav_path) if wav_path else "None",
            )

            # Reset local buffer
            self._audio_frames_buffer.clear()
            self._active_audio_chunk_id = None

            # Publish VOICE_STOPPED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.VOICE_STOPPED,
                    source=self._name,
                    payload=VoicePayload(
                        audio_chunk_id=chunk_id,  # type: ignore[arg-type]
                        sample_rate=self._sample_rate,
                        duration_ms=duration_ms,
                        audio_segment_path=wav_path,
                    ),
                )
            )

    def _speech_duration_frames(self) -> int:
        """Returns min speech frame threshold."""
        return self._speech_frames_threshold

    def _write_wav_segment(self) -> str | None:
        """Write all active buffered frames to a temporary WAV file."""
        if not self._audio_frames_buffer:
            return None

        try:
            fd, path = tempfile.mkstemp(suffix=".wav", prefix="vad_speech_")
            os.close(fd)

            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self._bytes_per_sample)
                wf.setframerate(self._sample_rate)
                wf.writeframes(b"".join(self._audio_frames_buffer))

            return path
        except Exception as exc:
            logger.error("Failed to write temporary WAV audio segment: %s", exc)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Get health monitoring status."""
        with self._lock:
            status_str = "healthy" if self._microphone_connected else "degraded"
            if not self._running:
                status_str = "stopped"

            return {
                "status": status_str,
                "connected": self._microphone_connected,
                "is_mock": self._is_mock,
                "dropped_frames": self._dropped_frames,
            }

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            uptime_sec = time.perf_counter() - self._start_time if self._start_time else 0.0
            avg_latency = (
                self._total_process_ms / self._frames_processed if self._frames_processed > 0 else 0.0
            )

            return {
                "is_speaking": self._is_speaking,
                "frames_processed": self._frames_processed,
                "dropped_frames": self._dropped_frames,
                "average_processing_latency_ms": round(avg_latency, 3),
                "speech_duration_seconds": round(self._speech_duration_sec, 2),
                "silence_duration_seconds": round(self._silence_duration_sec, 2),
                "uptime_seconds": round(uptime_sec, 3),
                "health": self.health(),
            }
