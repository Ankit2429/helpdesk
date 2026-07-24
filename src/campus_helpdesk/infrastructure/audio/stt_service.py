"""Offline Speech-to-Text service interface and PyTorch Whisper implementation."""

import logging
from typing import Optional, Protocol

from campus_helpdesk.infrastructure.audio.tts_service import TTSService

logger = logging.getLogger(__name__)


class STTService(Protocol):
    """Protocol for speech-to-text transcription."""

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes to text string."""

    def listen_and_transcribe(
        self,
        timeout: int = 8,
        phrase_time_limit: int = 15,
        tts_service: Optional[TTSService] = None,
    ) -> str:
        """Record directly from microphone and transcribe speech to text."""


class FasterWhisperSTTService:
    """Production-ready STT service backed by HuggingFace PyTorch Whisper."""

    def __init__(
        self,
        model_size: str = "openai/whisper-tiny",
        device: str = "cpu",
        compute_type: str = "float32",
        device_index: int | None = None,
        enable_online_fallback: bool = False,
        debug: bool = False,
    ) -> None:
        self._model_name = model_size if "/" in model_size else f"openai/whisper-{model_size}"
        self._device = device
        self._device_index = device_index
        self._enable_online_fallback = enable_online_fallback
        self._debug = debug
        self._processor = None
        self._model = None
        self._init_model()

    def _init_model(self) -> None:
        """Initialize local HuggingFace PyTorch Whisper model and processor."""
        try:
            import torch
            from transformers import WhisperForConditionalGeneration, WhisperProcessor

            logger.info(f"[INFO] Loading PyTorch HuggingFace Whisper model '{self._model_name}' on {self._device}...")
            self._processor = WhisperProcessor.from_pretrained(self._model_name)
            self._model = WhisperForConditionalGeneration.from_pretrained(self._model_name).to(self._device)
            self._model.eval()
            logger.info("[INFO] PyTorch HuggingFace Whisper STT model initialized successfully!")
        except Exception as e:
            logger.error(f"[ERROR] Whisper model initialization failed: {e}", exc_info=True)
            self._processor = None
            self._model = None

    def enumerate_microphones(self) -> list[tuple[int, str]]:
        """Enumerate all system input devices."""
        try:
            import speech_recognition as sr
            mic_names = sr.Microphone.list_microphone_names()
            logger.info(f"[INFO] Enumerating {len(mic_names)} microphones...")
            devices = []
            for idx, name in enumerate(mic_names):
                logger.info(f"  [{idx}]: '{name}'")
                devices.append((idx, name))
            return devices
        except Exception as e:
            logger.error(f"[ERROR] Microphone enumeration failed: {e}")
            return []

    def _select_microphone(self) -> int | None:
        """Select best physical recording device, bypassing virtual/loopback drivers."""
        if self._device_index is not None:
            logger.info(f"[INFO] Using configured microphone index: {self._device_index}")
            return self._device_index

        devices = self.enumerate_microphones()
        if not devices:
            logger.error("[ERROR] No microphone found on system.")
            return None

        # Filter out virtual/loopback devices
        candidate_idx = None
        for idx, name in devices:
            name_lower = name.lower()
            if any(bad in name_lower for bad in ["fxsound", "mapper", "stereo mix", "virtual", "steam"]):
                continue
            if "realtek" in name_lower or "microphone array" in name_lower or "microphone" in name_lower:
                candidate_idx = idx
                logger.info(f"[INFO] Automatically selected microphone [{idx}]: '{name}'")
                break

        if candidate_idx is None and devices:
            candidate_idx = devices[0][0]
            logger.info(f"[INFO] Using default physical microphone [{candidate_idx}]: '{devices[0][1]}'")

        return candidate_idx

    def _open_microphone(self, device_index: int | None):
        """Construct SpeechRecognition Microphone instance."""
        import speech_recognition as sr
        mic_kwargs = {"device_index": device_index} if device_index is not None else {}
        return sr.Microphone(**mic_kwargs)

    def _calibrate_microphone(self, recognizer, source, duration: float = 1.0) -> None:
        """Calibrate recognizer energy thresholds for ambient noise."""
        logger.info(f"[INFO] Calibrating ambient noise ({duration}s)...")
        recognizer.adjust_for_ambient_noise(source, duration=duration)
        recognizer.energy_threshold = max(recognizer.energy_threshold, 100)
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.phrase_threshold = 0.3
        recognizer.non_speaking_duration = 0.5

    def _record_audio(self, recognizer, source, timeout: int = 8, phrase_time_limit: int = 15):
        """Capture live speech from microphone source."""
        import speech_recognition as sr
        logger.info(f"[INFO] Listening... (timeout={timeout}s, phrase_limit={phrase_time_limit}s)")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            logger.info("[INFO] Audio captured.")
            return audio
        except sr.WaitTimeoutError:
            logger.warning(f"[WARNING] Timeout waiting for speech after {timeout} seconds.")
            return None

    def _save_debug_audio(self, audio, filepath: str = "debug_capture.wav") -> None:
        """Save WAV audio debug capture file if debug mode is enabled."""
        if not self._debug or audio is None:
            return
        try:
            wav_data = audio.get_wav_data()
            with open(filepath, "wb") as f:
                f.write(wav_data)
            logger.info(f"[INFO] Saved {len(wav_data)} bytes of captured debug audio to '{filepath}'")
        except Exception as e:
            logger.warning(f"[WARNING] Failed to save debug WAV file: {e}")

    def _validate_audio(self, raw_pcm: bytes) -> bool:
        """Check whether captured audio PCM data contains non-silent signal."""
        if not raw_pcm:
            return False
        import numpy as np
        samples = np.frombuffer(raw_pcm, dtype=np.int16)
        if len(samples) == 0:
            return False
        rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        logger.info(f"[INFO] Captured audio signal RMS volume level: {rms:.2f}")
        # Allow any non-empty audio (RMS > 0.5) so normal/quiet speech is never falsely rejected
        return bool(rms > 0.5)

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw mono 16-bit PCM audio bytes using PyTorch Whisper model."""
        if not audio_data:
            logger.warning("[WARNING] Empty audio captured. Cannot run transcription.")
            return ""

        if not self._validate_audio(audio_data):
            logger.warning("[WARNING] Audio signal volume too quiet or silent. Skipping transcription.")
            return ""

        logger.info("[INFO] Running Whisper transcription...")
        if self._model is not None and self._processor is not None:
            try:
                import numpy as np
                import torch

                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                inputs = self._processor(audio_np, sampling_rate=sample_rate, return_tensors="pt")
                input_features = inputs.input_features.to(self._device)

                with torch.no_grad():
                    predicted_ids = self._model.generate(input_features)

                transcription = self._processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
                if transcription:
                    logger.info(f"[INFO] Transcript: '{transcription}'")
                    return transcription
                else:
                    logger.warning("[WARNING] Whisper model returned empty transcription.")
            except Exception as e:
                logger.error(f"[ERROR] Whisper model failed: {e}", exc_info=True)

        if self._enable_online_fallback:
            try:
                import speech_recognition as sr
                logger.info("[INFO] ENABLE_ONLINE_FALLBACK=True. Attempting Google Speech API fallback...")
                recognizer = sr.Recognizer()
                audio_instance = sr.AudioData(audio_data, sample_rate, 2)
                transcript = recognizer.recognize_google(audio_instance).strip()
                logger.info(f"[INFO] Google Fallback Transcript: '{transcript}'")
                return transcript
            except Exception as e:
                logger.warning(f"[WARNING] Google Speech API fallback failed: {e}")
        else:
            logger.info("[INFO] Offline mode enforced (ENABLE_ONLINE_FALLBACK=False).")

        return ""

    def listen_and_transcribe(
        self,
        timeout: int = 8,
        phrase_time_limit: int = 15,
        tts_service: Optional[TTSService] = None,
    ) -> str:
        """Record live audio from microphone and transcribe speech to text."""
        if tts_service is not None and hasattr(tts_service, "is_speaking"):
            if tts_service.is_speaking():
                logger.info("[INFO] Waiting for TTS audio playback to complete before opening microphone...")
                if hasattr(tts_service, "wait_until_done"):
                    tts_service.wait_until_done(timeout=10.0)

        device_index = self._select_microphone()
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            mic = self._open_microphone(device_index)

            with mic as source:
                self._calibrate_microphone(recognizer, source, duration=1.0)
                audio = self._record_audio(recognizer, source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            if audio is None:
                return ""

            self._save_debug_audio(audio)
            raw_pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
            transcript = self.transcribe_audio(raw_pcm, sample_rate=16000)
            return transcript

        except AttributeError as e:
            logger.error(f"[ERROR] Permission denied or PyAudio driver error: {e}")
            return ""
        except Exception as err:
            logger.error(f"[ERROR] Microphone capture error ({type(err).__name__}): {err}", exc_info=True)
            return ""