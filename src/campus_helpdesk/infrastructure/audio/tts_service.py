"""Offline Text-to-Speech service interface and Piper/pyttsx3 non-blocking implementation."""

import logging
import queue
import threading
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class TTSService(Protocol):
    """Protocol for offline text-to-speech synthesis."""

    def speak(self, text: str) -> None:
        """Synthesize and play speech asynchronously without blocking UI."""

    def stop(self) -> None:
        """Stop current speech output."""

    def is_speaking(self) -> bool:
        """Return True if TTS engine is currently speaking audio."""

    def wait_until_done(self, timeout: float = 10.0) -> None:
        """Block until current TTS audio playback finishes."""


class NonBlockingTTSService:
    """Non-blocking TTS service. Uses real Piper neural voices when the model
    files are present; falls back to the system pyttsx3 engine otherwise."""

    def __init__(
        self,
        voice_model: str = "en_US-lessac-medium",
        piper_models_dir: str = "data/piper",
        use_cuda: bool = False,
    ) -> None:
        self._voice_model = voice_model
        self._piper_models_dir = Path(piper_models_dir)
        self._use_cuda = use_cuda
        self._speech_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._is_speaking_flag = False
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._speech_loop, daemon=True)
        self._worker_thread.start()

    def _load_piper_voice(self):
        """Attempt to load the configured Piper ONNX voice model from disk."""
        model_path = self._piper_models_dir / f"{self._voice_model}.onnx"
        config_path = self._piper_models_dir / f"{self._voice_model}.onnx.json"

        if not model_path.exists() or not config_path.exists():
            logger.warning(
                f"[WARNING] Piper voice files not found for '{self._voice_model}' "
                f"(expected {model_path} + .json). Falling back to pyttsx3. "
                f"See docs/MODEL_SETUP.md to download the voice."
            )
            return None

        try:
            from piper.voice import PiperVoice

            voice = PiperVoice.load(str(model_path), config_path=str(config_path), use_cuda=self._use_cuda)
            logger.info(f"[INFO] Piper voice '{self._voice_model}' loaded successfully.")
            return voice
        except Exception as e:
            logger.error(f"[ERROR] Piper voice load failed: {e}", exc_info=True)
            return None

    def _speak_piper(self, voice, text: str) -> None:
        """Synthesize with Piper and stream audio out directly to persistent PyAudio stream."""
        import pyaudio

        if not hasattr(self, "_pa") or self._pa is None:
            self._pa = pyaudio.PyAudio()
            self._pa_stream = None

        try:
            for chunk in voice.synthesize(text):
                if self._pa_stream is None:
                    self._pa_stream = self._pa.open(
                        format=self._pa.get_format_from_width(chunk.sample_width),
                        channels=chunk.sample_channels,
                        rate=chunk.sample_rate,
                        output=True,
                    )
                if self._stop_event.is_set():
                    break
                self._pa_stream.write(chunk.audio_int16_bytes)
        except Exception as err:
            logger.error(f"Piper audio stream error: {err}")

    def _speech_loop(self) -> None:
        """Background worker thread executing speech requests."""
        piper_voice = self._load_piper_voice()
        pyttsx3_engine = None

        if piper_voice is None:
            try:
                import pyttsx3

                pyttsx3_engine = pyttsx3.init()
            except Exception as e:
                logger.warning(f"pyttsx3 engine init failed: {e}")

        while not self._stop_event.is_set():
            try:
                text = self._speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not text:
                continue

            with self._lock:
                self._is_speaking_flag = True

            logger.info(f"TTS Speaking: '{text[:40]}...'")

            try:
                if piper_voice is not None:
                    self._speak_piper(piper_voice, text)
                elif pyttsx3_engine is not None:
                    pyttsx3_engine.say(text)
                    pyttsx3_engine.runAndWait()
                else:
                    logger.info(f"[TTS Fallback Simulation] Spoke: {text}")
            except Exception as err:
                logger.error(f"TTS Engine synthesis error: {err}", exc_info=True)
            finally:
                with self._lock:
                    self._is_speaking_flag = False
                self._speech_queue.task_done()

    def speak(self, text: str) -> None:
        """Enqueue speech request non-blockingly."""
        if text.strip():
            self._speech_queue.put(text)

    def stop(self) -> None:
        """Clear queued speech requests."""
        with self._speech_queue.mutex:
            self._speech_queue.queue.clear()
        with self._lock:
            self._is_speaking_flag = False

    def is_speaking(self) -> bool:
        """Return True if TTS engine is currently playing speech or has queued speech."""
        with self._lock:
            return self._is_speaking_flag or not self._speech_queue.empty()

    def wait_until_done(self, timeout: float = 10.0) -> None:
        """Block caller thread until all TTS speech completes or timeout expires."""
        import time
        start_time = time.time()
        while self.is_speaking() and (time.time() - start_time) < timeout:
            time.sleep(0.1)