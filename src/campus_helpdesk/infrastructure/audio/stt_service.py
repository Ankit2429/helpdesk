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
    """STT service backed by HuggingFace PyTorch Whisper (bypasses Windows DLL policy blocks)."""

    def __init__(
        self,
        model_size: str = "openai/whisper-tiny",
        device: str = "cpu",
        compute_type: str = "float32",
        allow_online_fallback: bool = False,
    ) -> None:
        self._model_name = "openai/whisper-tiny" if "openai" not in model_size else model_size
        self._device = device
        self._processor = None
        self._model = None
        self._allow_online_fallback = allow_online_fallback
        self._init_model()

    def _init_model(self) -> None:
        """Initialize local HuggingFace PyTorch Whisper model and processor."""
        try:
            import torch
            from transformers import WhisperForConditionalGeneration, WhisperProcessor

            logger.info(f"Loading PyTorch HuggingFace Whisper model '{self._model_name}' on {self._device}...")
            self._processor = WhisperProcessor.from_pretrained(self._model_name)
            self._model = WhisperForConditionalGeneration.from_pretrained(self._model_name).to(self._device)
            self._model.eval()
            logger.info("PyTorch HuggingFace Whisper STT model initialized successfully!")
        except Exception as e:
            logger.error(f"PyTorch Whisper model initialization failed: {e}")
            self._processor = None
            self._model = None

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw mono 16-bit PCM audio bytes using local PyTorch Whisper model."""
        if not audio_data:
            return ""

        if self._model is not None and self._processor is not None:
            try:
                import numpy as np
                import torch

                # Convert 16-bit PCM bytes to float32 numpy array normalized to [-1.0, 1.0]
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                inputs = self._processor(audio_np, sampling_rate=sample_rate, return_tensors="pt")
                input_features = inputs.input_features.to(self._device)

                with torch.no_grad():
                    predicted_ids = self._model.generate(input_features)

                transcription = self._processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
                if transcription:
                    logger.info(f"[PyTorch Whisper Transcript]: '{transcription}'")
                    return transcription
            except Exception as e:
                logger.error(f"PyTorch Whisper transcription error: {e}")

        # [ONLINE DEPENDENCY] Google Web API fallback — requires internet.
        # Guarded by allow_online_fallback; production offline mode skips this entirely.
        if self._allow_online_fallback:
            try:
                import speech_recognition as sr

                recognizer = sr.Recognizer()
                audio_instance = sr.AudioData(audio_data, sample_rate, 2)
                transcript = recognizer.recognize_google(audio_instance).strip()
                logger.info(f"[Google Web API Fallback Transcript]: '{transcript}'")
                return transcript
            except Exception as e:
                logger.warning(f"Google Web API fallback failed: {e}")
        else:
            logger.warning("[STT Offline] Local Whisper unavailable and online fallback disabled. Cannot transcribe.")

        return ""

    def listen_and_transcribe(
        self,
        timeout: int = 8,
        phrase_time_limit: int = 15,
        tts_service: Optional[TTSService] = None,
    ) -> str:
        """Record live audio from system microphone and transcribe using PyTorch Whisper model."""
        # 1. Full-Duplex Protection: Ensure TTS speech finishes completely before opening microphone
        if tts_service is not None and hasattr(tts_service, "is_speaking"):
            if tts_service.is_speaking():
                logger.info("[Full-Duplex Interlock] TTS is currently speaking. Waiting for TTS audio output to complete before opening microphone...")
                if hasattr(tts_service, "wait_until_done"):
                    tts_service.wait_until_done(timeout=10.0)

        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            mic_names = sr.Microphone.list_microphone_names()
            logger.info(f"[STT Mic Check] Enumerated {len(mic_names)} audio input devices:")
            for idx, name in enumerate(mic_names):
                logger.info(f"  Device [{idx}]: '{name}'")

            # Explicitly select physical hardware mic (bypassing virtual sound drivers like FxSound)
            target_device_index = None
            for idx, name in enumerate(mic_names):
                name_lower = name.lower()
                if "fxsound" in name_lower or "mapper" in name_lower or "stereo mix" in name_lower:
                    continue
                if "realtek" in name_lower or "microphone array" in name_lower or ("microphone" in name_lower and "virtual" not in name_lower):
                    target_device_index = idx
                    break

            mic_kwargs = {"device_index": target_device_index} if target_device_index is not None else {}

            with sr.Microphone(**mic_kwargs) as source:
                device_idx = source.device_index
                device_label = mic_names[device_idx] if device_idx is not None and device_idx < len(mic_names) else "Default Input"
                logger.info(f"[STT Mic Active Device] Index {device_idx}: '{device_label}'")

                logger.info("[STT Mic Calibration] Calibrating ambient noise (1.0s)...")
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                # Lower energy threshold for better sensitivity on typical laptop mics
                recognizer.energy_threshold = max(recognizer.energy_threshold * 0.7, 200)
                recognizer.dynamic_energy_threshold = True
                recognizer.pause_threshold = 0.8

                logger.info(f"[STT Listening] Listening for user speech (timeout={timeout}s, phrase_limit={phrase_time_limit}s)...")
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

                # Save captured WAV debug file
                try:
                    wav_data = audio.get_wav_data()
                    with open("debug_capture.wav", "wb") as f:
                        f.write(wav_data)
                    logger.info(f"[STT Debug] Saved {len(wav_data)} bytes of captured audio to 'debug_capture.wav'")
                except Exception as save_err:
                    logger.warning(f"Failed to save debug_capture.wav: {save_err}")

            # 2. Transcribe using local PyTorch Whisper model if available
            transcript = ""
            if self._model is not None:
                raw_pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
                transcript = self.transcribe_audio(raw_pcm, sample_rate=16000)

            # 3. [ONLINE DEPENDENCY] Google Web API fallback — requires internet.
            #    Guarded by allow_online_fallback; production offline mode skips this entirely.
            if not transcript and self._allow_online_fallback:
                try:
                    logger.info("[STT Transcribing] Attempting Google Web API recognition...")
                    transcript = recognizer.recognize_google(audio, language="en-US").strip()
                    if transcript:
                        logger.info(f"[STT Success] Google Web API transcript: '{transcript}'")
                        return transcript
                except sr.UnknownValueError:
                    logger.warning("[STT Failure] Google Speech API: Audio captured, but speech was unintelligible or silence.")
                except sr.RequestError as req_err:
                    logger.warning(f"[STT Failure] Google Speech API request error: {req_err}")
                except Exception as google_err:
                    logger.warning(f"[STT Failure] Google Web API exception: {google_err}")
            elif not transcript:
                logger.warning("[STT Offline] Local Whisper unavailable and online fallback disabled. Cannot transcribe.")

            return transcript
        except sr.WaitTimeoutError:
            logger.warning(f"[STT Timeout] Listening timed out after {timeout} seconds without hearing speech.")
            return ""
        except Exception as err:
            logger.error(f"[STT Error] Unexpected microphone capture error ({type(err).__name__}): {err}", exc_info=True)
            return ""





