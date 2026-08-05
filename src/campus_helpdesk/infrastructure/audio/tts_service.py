"""Offline Text-to-Speech service interface and Piper/pyttsx3 non-blocking implementation."""

import logging
import queue
import threading
from pathlib import Path
from typing import Any, Protocol

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
    """Non-blocking multilingual TTS service.

    Uses Piper ONNX neural voices for English and Hindi when available;
    falls back to pyttsx3 system engine for Kannada (no Piper Kannada voice exists)
    or if model files are missing.
    """

    VOICE_MAP = {
        "en": "en_US-lessac-medium",
        "en_US": "en_US-lessac-medium",
        "hi": "hi_IN-pratham-medium",
        "hi_IN": "hi_IN-pratham-medium",
    }

    def __init__(
        self,
        voice_model: str = "en_US-lessac-medium",
        piper_models_dir: str = "data/piper",
        use_cuda: bool = False,
        on_speaking_state_changed: Any | None = None,
    ) -> None:
        self._default_voice_model = voice_model
        self._piper_models_dir = Path(piper_models_dir)
        self._use_cuda = use_cuda
        self._on_speaking_state_changed = on_speaking_state_changed
        self._speech_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._stop_event = threading.Event()
        self._is_speaking_flag = False
        self._lock = threading.Lock()
        self._piper_voices: dict[str, Any] = {}
        self._pyttsx3_engine = None
        self._worker_thread = threading.Thread(target=self._speech_loop, daemon=True)
        self._worker_thread.start()

    def _load_piper_voice(self, model_name: str):
        """Attempt to load a configured Piper ONNX voice model from disk with caching."""
        if model_name in self._piper_voices:
            return self._piper_voices[model_name]

        model_path = self._piper_models_dir / f"{model_name}.onnx"
        config_path = self._piper_models_dir / f"{model_name}.onnx.json"

        if not model_path.exists() or not config_path.exists():
            logger.warning(
                f"[WARNING] Piper voice files missing for '{model_name}' "
                f"(expected {model_path} + .json). Falling back to system pyttsx3 engine."
            )
            return None

        try:
            from piper.voice import PiperVoice

            voice = PiperVoice.load(str(model_path), config_path=str(config_path), use_cuda=self._use_cuda)
            self._piper_voices[model_name] = voice
            logger.info(f"[INFO] Piper voice '{model_name}' loaded successfully.")
            return voice
        except Exception as e:
            logger.error(f"[ERROR] Piper voice load failed for '{model_name}': {e}", exc_info=True)
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
            logger.error(f"Piper audio stream error: {err}", exc_info=True)

    def _get_pyttsx3_engine(self):
        if self._pyttsx3_engine is None:
            try:
                import pyttsx3

                self._pyttsx3_engine = pyttsx3.init()
            except Exception as e:
                logger.warning(f"pyttsx3 engine init failed: {e}")
        return self._pyttsx3_engine

    def _speech_loop(self) -> None:
        """Background worker thread executing speech requests."""
        while not self._stop_event.is_set():
            try:
                item = self._speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not item:
                continue

            text, lang = item if isinstance(item, tuple) else (str(item), "en")
            if not text.strip():
                continue

            was_speaking = False
            with self._lock:
                was_speaking = self._is_speaking_flag
                self._is_speaking_flag = True

            if not was_speaking and self._on_speaking_state_changed:
                try:
                    self._on_speaking_state_changed(True)
                except Exception as cb_err:
                    logger.warning(f"Error in on_speaking_state_changed(True): {cb_err}")

            logger.info(f"TTS Speaking [{lang}]: '{text[:40]}...'")

            try:
                voice_name = self.VOICE_MAP.get(lang.lower(), self._default_voice_model)
                piper_voice = None

                if lang.lower() in ("kn", "kn_in"):
                    logger.warning(
                        f"[WARNING] Piper has no official voice model for Kannada ('{lang}'). "
                        "Falling back to system pyttsx3 engine."
                    )
                else:
                    piper_voice = self._load_piper_voice(voice_name)

                pyttsx3_engine = self._get_pyttsx3_engine()

                if piper_voice is not None:
                    self._speak_piper(piper_voice, text)
                elif pyttsx3_engine is not None:
                    pyttsx3_engine.say(text)
                    pyttsx3_engine.runAndWait()
                else:
                    logger.info(f"[TTS Fallback Simulation] Spoke [{lang}]: {text}")
            except Exception as err:
                logger.error(f"TTS Engine synthesis error: {err}", exc_info=True)
            finally:
                self._speech_queue.task_done()
                if self._speech_queue.empty():
                    with self._lock:
                        self._is_speaking_flag = False
                    if self._on_speaking_state_changed:
                        try:
                            self._on_speaking_state_changed(False)
                        except Exception as cb_err:
                            logger.warning(f"Error in on_speaking_state_changed(False): {cb_err}")

    def speak(self, text: str, language: str = "en") -> None:
        """Enqueue speech request non-blockingly with optional language code."""
        if text.strip():
            self._speech_queue.put((text, language))

    def speak_stream(self, token_generator, language: str = "en") -> None:
        """Stream sentence-level speech directly from LLM token generator."""
        import re

        sentence_buffer = ""
        sentence_delimiters = re.compile(r"([.?!:\n])")

        def _stream_processor():
            nonlocal sentence_buffer
            for token in token_generator:
                if self._stop_event.is_set():
                    break
                sentence_buffer += token
                # Check for sentence completion boundaries
                parts = sentence_delimiters.split(sentence_buffer)
                if len(parts) > 1:
                    # Enqueue complete sentence segments
                    for i in range(0, len(parts) - 1, 2):
                        sentence = (parts[i] + parts[i + 1]).strip()
                        if sentence:
                            self.speak(sentence, language=language)
                    sentence_buffer = parts[-1]

            # Enqueue any remaining tail content
            if sentence_buffer.strip() and not self._stop_event.is_set():
                self.speak(sentence_buffer.strip(), language=language)

        threading.Thread(target=_stream_processor, daemon=True, name="TTS-StreamProcessor").start()

    def stop(self) -> None:
        """Clear queued speech requests and cancel active playback (barge-in)."""
        self.cancel_playback()

    def cancel_playback(self) -> None:
        """Instantly stop all TTS audio playback and flush speech queue for barge-in."""
        with self._speech_queue.mutex:
            self._speech_queue.queue.clear()
        
        self._stop_event.set()
        
        if hasattr(self, "_pa_stream") and self._pa_stream is not None:
            try:
                self._pa_stream.stop_stream()
            except Exception:
                pass

        with self._lock:
            self._is_speaking_flag = False

        # Reset stop event for subsequent speech calls
        self._stop_event.clear()

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