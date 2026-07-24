"""Offline Speech-to-Text service interface and Faster-Whisper implementation."""

import logging
import tempfile
import wave
from typing import Protocol

logger = logging.getLogger(__name__)


class STTService(Protocol):
    """Protocol for speech-to-text transcription."""

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes to text string."""

    def listen_and_transcribe(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """Record directly from microphone and transcribe speech to text."""


class FasterWhisperSTTService:
    """STT implementation backed by Faster-Whisper with SpeechRecognition fallback."""

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
        """Lazy load the Faster-Whisper model with fallback handling."""
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
                f"Faster-Whisper model initialization unavailable ({e}). Using SpeechRecognition Google Web API fallback."
            )
            self._model = None

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
                if transcript:
                    return transcript
            except Exception as e:
                logger.error(f"Faster-Whisper transcription error: {e}")

        # 1. Primary Fallback: SpeechRecognition Google Web API
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            audio_instance = sr.AudioData(audio_data, sample_rate, 2)
            transcript = recognizer.recognize_google(audio_instance).strip()
            if transcript:
                logger.info(f"SpeechRecognition Google Web API transcript: '{transcript}'")
                return transcript
        except Exception as e:
            logger.debug(f"SpeechRecognition Google Web API fallback failed/offline: {e}")

        # 2. Secondary Offline Fallback: SpeechRecognition PocketSphinx
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            audio_instance = sr.AudioData(audio_data, sample_rate, 2)
            transcript = recognizer.recognize_sphinx(audio_instance).strip()
            if transcript:
                logger.info(f"SpeechRecognition PocketSphinx offline transcript: '{transcript}'")
                return transcript
        except Exception as e:
            logger.debug(f"SpeechRecognition PocketSphinx offline fallback failed: {e}")

        return ""

    def listen_and_transcribe(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """Record live audio from system microphone and transcribe using Google API or Sphinx offline."""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                logger.info("Microphone active: Listening for user speech...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            # Try Google Web API first
            try:
                transcript = recognizer.recognize_google(audio).strip()
                if transcript:
                    logger.info(f"Microphone Google API transcription success: '{transcript}'")
                    return transcript
            except Exception as google_err:
                logger.debug(f"Google Web API offline/unavailable: {google_err}")

            # Try Sphinx offline fallback second
            try:
                transcript = recognizer.recognize_sphinx(audio).strip()
                if transcript:
                    logger.info(f"Microphone Sphinx offline transcription success: '{transcript}'")
                    return transcript
            except Exception as sphinx_err:
                logger.debug(f"Sphinx offline fallback failed: {sphinx_err}")

            return ""
        except Exception as err:
            logger.warning(f"Microphone recording/transcription failed: {err}")
            return ""


