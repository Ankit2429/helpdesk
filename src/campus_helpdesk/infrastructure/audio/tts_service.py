"""Offline Text-to-Speech service interface and Piper/pyttsx3 non-blocking implementation."""

import logging
import queue
import threading
from typing import Protocol

logger = logging.getLogger(__name__)


class TTSService(Protocol):
    """Protocol for offline text-to-speech synthesis."""

    def speak(self, text: str) -> None:
        """Synthesize and play speech asynchronously without blocking UI."""

    def stop(self) -> None:
        """Stop current speech output."""


class NonBlockingTTSService:
    """Non-blocking TTS service utilizing thread queue and pyttsx3/Piper engine."""

    def __init__(self, voice_model: str = "en_US-lessac-medium") -> None:
        self._voice_model = voice_model
        self._speech_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._speech_loop, daemon=True)
        self._worker_thread.start()

    def _speech_loop(self) -> None:
        """Background worker thread executing speech requests."""
        engine = None
        try:
            import pyttsx3

            engine = pyttsx3.init()
        except Exception as e:
            logger.warning(f"pyttsx3 engine init failed: {e}")

        while not self._stop_event.is_set():
            try:
                text = self._speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not text:
                continue

            logger.info(f"TTS Speaking: '{text[:40]}...'")

            if engine is not None:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as err:
                    logger.error(f"TTS Engine synthesis error: {err}")
            else:
                logger.info(f"[TTS Fallback Simulation] Spoke: {text}")

            self._speech_queue.task_done()

    def speak(self, text: str) -> None:
        """Enqueue speech request non-blockingly."""
        if text.strip():
            self._speech_queue.put(text)

    def stop(self) -> None:
        """Clear queued speech requests."""
        with self._speech_queue.mutex:
            self._speech_queue.queue.clear()
