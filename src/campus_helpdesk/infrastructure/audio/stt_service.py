"""Offline Speech-to-Text service interface and Faster-Whisper implementation."""

import logging
import tempfile
import wave
from typing import Protocol

logger = logging.getLogger(__name__)


class STTService(Protocol):
    """Protocol for offline speech-to-text transcription."""

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes to text string."""


class FasterWhisperSTTService:
    """Offline STT implementation backed by Faster-Whisper with fallback support."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._init_model()

    def _init_model(self) -> None:
        """Lazy load the Faster-Whisper model."""
        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading Faster-Whisper model '{self._model_size}' on {self._device}...")
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                local_files_only=True,
            )
        except Exception as e:
            logger.warning(
                f"Faster-Whisper model init warning (will attempt standard speech recognition or fallback): {e}"
            )

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw mono 16-bit PCM audio bytes."""
        if not audio_data:
            return ""

        if self._model is not None:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                    with wave.open(temp_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit PCM
                        wf.setframerate(sample_rate)
                        wf.writeframes(audio_data)

                segments, _ = self._model.transcribe(temp_path, beam_size=5)
                transcript = " ".join([segment.text for segment in segments]).strip()
                return transcript
            except Exception as e:
                logger.error(f"Faster-Whisper transcription error: {e}")

        # Fallback transcription using speech_recognition if installed
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            audio_instance = sr.AudioData(audio_data, sample_rate, 2)
            return recognizer.recognize_sphinx(audio_instance)
        except Exception as e:
            logger.warning(f"Fallback speech recognition unavailable/failed: {e}")

        return ""
