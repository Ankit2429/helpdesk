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

    def listen_and_transcribe_stream(
        self,
        callback,
        stop_event,
        tts_service: Optional[TTSService] = None,
    ) -> None:
        """Stream record from microphone and transcribe in real-time."""


class STTResult(str):
    """String subclass containing transcription text and detected language metadata."""

    def __new__(cls, text: str, language: str = "en", confidence: float = 1.0):
        obj = super().__new__(cls, text)
        obj.text = text
        obj.language = language
        obj.confidence = confidence
        return obj

    @property
    def language_code(self) -> str:
        return self.language

    def to_tuple(self) -> tuple[str, str, float]:
        return (self.text, self.language, self.confidence)


class FasterWhisperSTTService:
    """Production-ready STT service backed by faster-whisper CTranslate2 engine."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        device_index: int | None = None,
        enable_online_fallback: bool = False,
        debug: bool = False,
    ) -> None:
        self._model_name = model_size
        if "/" in model_size:
            if "whisper-" in model_size:
                self._model_name = model_size.split("whisper-")[-1]
            else:
                self._model_name = "base"
        self._device = device
        self._device_index = device_index
        self._compute_type = compute_type
        self._enable_online_fallback = enable_online_fallback
        self._debug = debug
        self._model = None
        self._init_model()

    def _init_model(self) -> None:
        """Initialize local faster-whisper model."""
        try:
            from faster_whisper import WhisperModel

            logger.info(f"[INFO] Loading faster-whisper model '{self._model_name}' on {self._device} with compute type {self._compute_type}...")
            
            # CPU compatible compute types
            compute_type = self._compute_type
            if self._device == "cpu" and compute_type not in ["int8", "int8_float16", "int16", "float32"]:
                compute_type = "int8"

            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=compute_type,
                local_files_only=True,
            )
            logger.info("[INFO] faster-whisper STT model initialized successfully!")
        except Exception as e:
            logger.error(f"[ERROR] faster-whisper model initialization failed: {e}", exc_info=True)
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
        # Avoid setting the energy threshold too high or too low
        recognizer.energy_threshold = max(min(recognizer.energy_threshold, 300), 80)
        recognizer.dynamic_energy_threshold = False  # Disable to prevent dynamic drift
        recognizer.pause_threshold = 1.2             # Allow natural pauses during speech
        recognizer.phrase_threshold = 0.3
        recognizer.non_speaking_duration = 0.8

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

    def transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> STTResult:
        """Transcribe raw mono 16-bit PCM audio bytes using faster-whisper model.

        Auto-detects language if language is None, or uses provided language code (e.g. 'en', 'hi', 'kn').
        Returns STTResult (string subclass) with .language and .confidence metadata.
        """
        if not audio_data:
            logger.warning("[WARNING] Empty audio captured. Cannot run transcription.")
            return STTResult("", "en", 0.0)

        if not self._validate_audio(audio_data):
            logger.warning("[WARNING] Audio signal volume too quiet or silent. Skipping transcription.")
            return STTResult("", "en", 0.0)

        logger.info("[INFO] Running Whisper transcription...")
        if self._model is not None:
            try:
                import numpy as np

                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                transcribe_kwargs = {
                    "beam_size": 1,
                    "vad_filter": True,
                }
                if language:
                    transcribe_kwargs["language"] = language

                segments, info = self._model.transcribe(audio_np, **transcribe_kwargs)
                
                detected_lang = getattr(info, "language", "en")
                lang_probability = float(getattr(info, "language_probability", 1.0))
                logger.info(f"[INFO] Detected language: '{detected_lang}' (probability={lang_probability:.2f})")

                if getattr(info, "no_speech_prob", 0) > 0.6:
                    logger.info(f"[INFO] High no_speech_prob ({info.no_speech_prob:.2f}). Skipping.")
                    return STTResult("", detected_lang, lang_probability)

                segments_list = list(segments)
                transcription = "".join(segment.text for segment in segments_list).strip()

                if transcription:
                    logger.info(f"[INFO] Transcript ({detected_lang}): '{transcription}'")
                    return STTResult(transcription, detected_lang, lang_probability)
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
                transcript = recognizer.recognize_google(audio_instance, language=language or "en-IN").strip()
                logger.info(f"[INFO] Google Fallback Transcript: '{transcript}'")
                return STTResult(transcript, language or "en", 0.90)
            except Exception as e:
                logger.warning(f"[WARNING] Google Speech API fallback failed: {e}")
        else:
            logger.info("[INFO] Offline mode enforced (ENABLE_ONLINE_FALLBACK=False).")

        return STTResult("", "en", 0.0)

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

    def listen_and_transcribe_stream(
        self,
        callback,
        stop_event,
        tts_service: Optional[TTSService] = None,
    ) -> None:
        """Stream record from microphone and transcribe in real-time, calling callback with updates."""
        if tts_service is not None and hasattr(tts_service, "is_speaking"):
            if tts_service.is_speaking():
                logger.info("[INFO] Waiting for TTS audio playback to complete before opening microphone...")
                if hasattr(tts_service, "wait_until_done"):
                    tts_service.wait_until_done(timeout=10.0)

        import pyaudio
        import numpy as np
        import time

        device_index = self._select_microphone()
        
        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )
        except Exception as e:
            logger.error(f"[ERROR] Failed to open PyAudio input stream: {e}")
            pa.terminate()
            callback("", True)
            return

        logger.info("[INFO] Real-time voice stream recording started...")
        
        audio_buffer = bytearray()
        last_transcribe_time = time.time()
        last_speech_time = time.time()
        last_text = ""
        
        energy_threshold = 120.0
        
        # Give a small calibration offset
        try:
            time.sleep(0.2)
            calibration_chunks = []
            for _ in range(3):
                cal_data = stream.read(1024, exception_on_overflow=False)
                cal_samples = np.frombuffer(cal_data, dtype=np.int16)
                if len(cal_samples) > 0:
                    calibration_chunks.append(np.sqrt(np.mean(cal_samples.astype(np.float32) ** 2)))
            if calibration_chunks:
                energy_threshold = max(np.mean(calibration_chunks) * 1.5, 100.0)
                logger.info(f"[INFO] Ambient noise calibrated. Energy threshold set to: {energy_threshold:.2f}")
        except Exception as cal_err:
            logger.warning(f"[WARNING] Calibration failed, using default energy threshold: {cal_err}")

        # Start the loop
        while not stop_event.is_set():
            try:
                # Read chunk
                data = stream.read(1024, exception_on_overflow=False)
                audio_buffer.extend(data)
                
                # Check volume level
                samples = np.frombuffer(data, dtype=np.int16)
                if len(samples) > 0:
                    rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
                    if rms > energy_threshold:
                        last_speech_time = time.time()
                
                # Transcribe every 0.25 seconds if we have new audio
                current_time = time.time()
                if current_time - last_transcribe_time > 0.25:
                    last_transcribe_time = current_time
                    
                    # Transcribe sliding window of accumulated audio
                    pcm_data = bytes(audio_buffer)
                    audio_np = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    prompt = "campus helpdesk, classroom, library, schedule, registration, cafeteria, office, course"
                    segments, info = self._model.transcribe(audio_np, beam_size=1, vad_filter=True, initial_prompt=prompt)
                    
                    if getattr(info, "no_speech_prob", 0) <= 0.6:
                        segments_list = list(segments)
                        text = "".join(segment.text for segment in segments_list).strip()
                        
                        # Filter out hallucinated prompt text
                        if any(bad in text.lower() for bad in ["campus helpdesk robot", "locate classrooms", "scheduling, registration"]):
                            text = ""
                        
                        if text and text != last_text:
                            last_text = text
                            callback(text, False)
                
                # Silence timeout: stop if silence exceeds 1.4 seconds and we got some text
                if last_text and (current_time - last_speech_time > 1.4):
                    logger.info("[INFO] Silence detected, auto-finalizing...")
                    break
                    
                # Absolute timeout: stop if absolute silence exceeds 5.0 seconds
                if not last_text and (current_time - last_speech_time > 5.0):
                    logger.info("[INFO] Silence timeout...")
                    break
                    
            except Exception as err:
                logger.error(f"[ERROR] Error in stream loop: {err}")
                break
                
        # Clean up
        try:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            pa.terminate()
        except Exception:
            pass
            
        # Final transcribe
        if audio_buffer and last_text:
            pcm_data = bytes(audio_buffer)
            audio_np = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            prompt = "campus helpdesk, classroom, library, schedule, registration, cafeteria, office, course"
            segments, info = self._model.transcribe(audio_np, beam_size=1, vad_filter=True, initial_prompt=prompt)
            if getattr(info, "no_speech_prob", 0) <= 0.6:
                segments_list = list(segments)
                final_text = "".join(segment.text for segment in segments_list).strip()
                if any(bad in final_text.lower() for bad in ["campus helpdesk robot", "locate classrooms", "scheduling, registration"]):
                    final_text = ""
                callback(final_text, True)
            else:
                callback("", True)
        else:
            callback("", True)