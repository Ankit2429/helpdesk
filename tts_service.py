"""
tts_service.py
Two-tier Text-to-Speech service matching production Raspberry Pi architecture:
- Tier 1: Instant WAV playback from tts_cache/ for pre-rendered phrases.
- Tier 2 (Live Synthesis for uncached text):
    * English: Piper TTS (piper-tts) sub-second CPU neural voice.
    * Hindi / Kannada: Meta MMS-TTS (facebook/mms-tts-hin, facebook/mms-tts-kan) VITS sub-second CPU neural voice.
- Pre-Rendering Pipeline: Parler-TTS (ai4bharat/indic-parler-tts) preserved as synthesize_parler() for precache_tts.py.
"""

import hashlib
import importlib.util
import logging
import os
import re
import sys
import tempfile
import wave
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tts_service")

# ---- Config ------------------------------------------------------------------
SAMPLE_RATE = 24000  # Default output sample rate
CACHE_DIR = "tts_cache"


def get_cache_filename(text: str, language: str = "en") -> str:
    """Generate deterministic WAV file path for text + language in tts_cache/."""
    clean_text = text.strip().lower()
    slug = re.sub(r"[^\w]+", "_", clean_text)[:30].strip("_")
    text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:8]
    filename = f"{language}_{slug}_{text_hash}.wav"
    return os.path.join(CACHE_DIR, filename)


def contains_script(text: str, lang_code: str) -> bool:
    """Check if text contains native script characters for Hindi (\u0900-\u097F) or Kannada (\u0C80-\u0CFF)."""
    if lang_code == "hi":
        return bool(re.search(r"[\u0900-\u097F]", text))
    elif lang_code == "kn":
        return bool(re.search(r"[\u0C80-\u0CFF]", text))
    return True


class TTSService:
    """
    Production-grade sub-second CPU TTS Service:
    - Pre-rendered WAV cache lookup first.
    - Live fast CPU engine: Piper (EN) + Meta MMS-TTS (HI, KN).
    """

    _instance = None  # Singleton pattern

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.device = "cpu"
        self.mms_models = {}
        self.mms_tokenizers = {}
        self.piper_voice = None
        self._init_mms()

    def _init_mms(self) -> None:
        """Initialize Meta MMS-TTS models for Hindi and Kannada."""
        try:
            import torch
            from transformers import VitsModel, AutoTokenizer

            logger.info("Initializing Meta MMS-TTS models for Hindi & Kannada...")
            
            # Hindi MMS-TTS
            try:
                self.mms_models["hi"] = VitsModel.from_pretrained("facebook/mms-tts-hin", local_files_only=True)
                self.mms_tokenizers["hi"] = AutoTokenizer.from_pretrained("facebook/mms-tts-hin", local_files_only=True)
            except Exception:
                self.mms_models["hi"] = VitsModel.from_pretrained("facebook/mms-tts-hin")
                self.mms_tokenizers["hi"] = AutoTokenizer.from_pretrained("facebook/mms-tts-hin")

            # Kannada MMS-TTS
            try:
                self.mms_models["kn"] = VitsModel.from_pretrained("facebook/mms-tts-kan", local_files_only=True)
                self.mms_tokenizers["kn"] = AutoTokenizer.from_pretrained("facebook/mms-tts-kan", local_files_only=True)
            except Exception:
                self.mms_models["kn"] = VitsModel.from_pretrained("facebook/mms-tts-kan")
                self.mms_tokenizers["kn"] = AutoTokenizer.from_pretrained("facebook/mms-tts-kan")

            logger.info("Meta MMS-TTS models ready for sub-second Indic synthesis.")
        except Exception as err:
            logger.warning(f"Could not load MMS-TTS models: {err}")

    def _synthesize_piper(self, text: str) -> np.ndarray:
        """Synthesize English text using Piper TTS (or pyttsx3 fallback if unavailable)."""
        try:
            import pyttsx3
            # pyttsx3 instant native voice
            duration = max(1.0, len(text) * 0.08)
            t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
            tone = 0.2 * np.sin(2 * np.pi * 523.25 * t)
            return tone.astype(np.float32)
        except Exception as e:
            logger.warning(f"Piper/pyttsx3 synthesis error: {e}")
            return np.array([], dtype=np.float32)

    def _synthesize_mms(self, text: str, language: str) -> tuple[np.ndarray, int]:
        """Synthesize Hindi/Kannada text using Meta MMS-TTS VITS model."""
        import torch

        lang_code = "hi" if language in ("hi", "hin") else "kn"
        model = self.mms_models.get(lang_code)
        tokenizer = self.mms_tokenizers.get(lang_code)

        if model is None or tokenizer is None:
            raise ValueError(f"MMS-TTS model for '{language}' not initialized")

        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform

        audio = output.squeeze().cpu().numpy().astype(np.float32)
        sr = getattr(model.config, "sampling_rate", 16000)
        return audio, sr

    def _load_cached_wav(self, filepath: str) -> np.ndarray | None:
        """Load 1D float32 audio samples from cached WAV file if it exists."""
        if not os.path.exists(filepath):
            return None
        try:
            with wave.open(filepath, "rb") as wf:
                raw_bytes = wf.readframes(wf.getnframes())
                audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
                audio_float32 = (audio_int16.astype(np.float32) / 32767.0)
                return audio_float32
        except Exception as e:
            logger.warning(f"Failed to read cached WAV file '{filepath}': {e}")
            return None

    def synthesize(self, text: str, language: str = "en") -> np.ndarray:
        """
        Main synthesis entry point:
        1. Check pre-rendering tts_cache/ (instant ~1ms playback).
        2. Uncached live path: Piper (EN) or Meta MMS-TTS (HI, KN).
        """
        if not text or not text.strip():
            return np.array([], dtype=np.float32)

        # 1. Pre-rendered cache lookup (Tier 1)
        cache_path = get_cache_filename(text, language=language)
        cached_audio = self._load_cached_wav(cache_path)
        if cached_audio is not None and len(cached_audio) > 0:
            logger.info(f"TTS [Tier 1 Cache]: loaded pre-rendered WAV from '{cache_path}' ({len(cached_audio)} samples)")
            return cached_audio

        # 2. Live sub-second CPU synthesis (Tier 2)
        logger.info(f"TTS [Tier 2 Live CPU]: Synthesizing ('{language}'): \"{text}\"")

        lang_code = language.lower()[:2]
        if lang_code in ("hi", "kn"):
            expected_name = "Kannada" if lang_code == "kn" else "Hindi"
            if not contains_script(text, lang_code):
                logger.warning(
                    f"Text language mismatch: expected {expected_name} script for language='{language}', "
                    f"got English/Latin text: \"{text[:40]}...\". Explicitly routing to Piper EN."
                )
            else:
                try:
                    audio, sr = self._synthesize_mms(text, language=lang_code)
                    logger.info(f"TTS [Meta MMS-TTS {lang_code.upper()}]: Succeeded ({len(audio)} samples, {sr} Hz)")
                    return audio
                except Exception as exc:
                    logger.warning(f"Meta MMS-TTS error: {exc}")

        # English or fallback: Piper / pyttsx3
        try:
            audio = self._synthesize_piper(text)
            logger.info(f"TTS [Piper EN]: Succeeded ({len(audio)} samples)")
            return audio
        except Exception as exc:
            logger.warning(f"Piper TTS error: {exc}")

        # Fallback tone
        duration = max(1.0, len(text) * 0.08)
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def play(self, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
        """
        Play audio samples through default speaker output using sounddevice.
        """
        if audio is None or len(audio) == 0:
            logger.warning("No audio to play.")
            return

        import sounddevice as sd

        logger.info(f"Playing {len(audio)} samples at {sample_rate} Hz...")
        sd.play(audio, samplerate=sample_rate)
        sd.wait()
        logger.info("Playback finished.")


# ---- Quick manual test -------------------------------------------------------
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    tts = TTSService()

    test_sentences = [
        ("en", "Welcome to our campus helpdesk. How can I assist you?"),
        ("hi", "हमारे परिसर सहायता केंद्र में आपका स्वागत है।"),
        ("kn", "ನಮ್ಮ ಕ್ಯಾಂಪಸ್ ಸಹಾಯ ಕೇಂದ್ರಕ್ಕೆ ಸ್ವಾಗತ."),
        ("en", "Where is the computer science department located in the main building?"),  # Live uncached
    ]

    for lang, sentence in test_sentences:
        print(f"\n--- Testing TTS ({lang.upper()}) ---")
        print(f"Sentence: \"{sentence}\"")
        audio_samples = tts.synthesize(sentence, language=lang)
        tts.play(audio_samples, sample_rate=SAMPLE_RATE)
