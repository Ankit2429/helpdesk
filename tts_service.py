"""
tts_service.py
Offline Text-to-Speech service using Indic Parler-TTS Mini (ai4bharat/indic-parler-tts).

Singleton class that loads Indic Parler-TTS once at import/init time,
exposing a `synthesize(text, language)` method that returns 1D float32 audio samples
and a `play(audio, sample_rate)` helper matching the style of stt_service.py.
"""

import logging
import os
import sys
import types
import importlib.util
import numpy as np

# Apply Windows AppLocker sentencepiece DLL bypass if necessary
try:
    import sentencepiece
except Exception:
    spm = types.ModuleType("sentencepiece")
    spm.__spec__ = importlib.util.spec_from_loader("sentencepiece", None)
    spm._sentencepiece = types.ModuleType("_sentencepiece")
    spm._sentencepiece.__spec__ = importlib.util.spec_from_loader("sentencepiece._sentencepiece", None)
    sys.modules["sentencepiece"] = spm
    sys.modules["sentencepiece._sentencepiece"] = spm._sentencepiece

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tts_service")

# ---- Config ------------------------------------------------------------------
INDIC_PARLER_TTS_MODEL = os.getenv("INDIC_PARLER_TTS_MODEL", "ai4bharat/indic-parler-tts")
DEFAULT_VOICE_PROMPT = os.getenv(
    "INDIC_TTS_VOICE_PROMPT",
    "A female speaker delivers a clear, articulate, and natural speech with a friendly tone."
)
SAMPLE_RATE = 24000  # Indic Parler-TTS default output sample rate


class TTSService:
    """
    Loads Indic Parler-TTS once and reuses it for every synthesis call.
    Exposes synthesize(text, language) -> np.ndarray and play(audio, sample_rate).
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

        self.model = None
        self.tokenizer = None
        self.description_tokenizer = None
        self.device = "cpu"
        self._init_model()

    def _init_model(self) -> None:
        """Load Indic Parler-TTS model and tokenizers."""
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer

            logger.info(f"Loading Indic Parler-TTS model='{INDIC_PARLER_TTS_MODEL}' (happens once)...")
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(
                INDIC_PARLER_TTS_MODEL
            ).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(INDIC_PARLER_TTS_MODEL)
            self.description_tokenizer = AutoTokenizer.from_pretrained(
                self.model.config.text_encoder._name_or_path
            )
            logger.info("Indic Parler-TTS model ready.")
        except Exception as err:
            logger.warning(f"Could not load Indic Parler-TTS model ({err}). Fallback TTS will be used if needed.")

    def synthesize(self, text: str, language: str = "en") -> np.ndarray:
        """
        Synthesize `text` into a mono 1D float32 NumPy array sampled at 24kHz.

        Args:
            text: Sentence string to speak.
            language: Language code ("en", "hi", "kn", etc.).

        Returns:
            np.ndarray: Audio samples (mono float32).
        """
        if not text or not text.strip():
            return np.array([], dtype=np.float32)

        logger.info(f"Synthesizing text ('{language}'): \"{text}\"")

        if self.model is not None and self.tokenizer is not None and self.description_tokenizer is not None:
            try:
                import torch

                description = f"A female speaker delivers a clear and natural speech in {language} with a friendly tone."
                
                input_ids = self.description_tokenizer(description, return_tensors="pt").input_ids.to(self.device)
                prompt_input_ids = self.tokenizer(text, return_tensors="pt").input_ids.to(self.device)

                with torch.no_grad():
                    generation = self.model.generate(
                        input_ids=input_ids,
                        prompt_input_ids=prompt_input_ids,
                    )
                
                audio = generation.cpu().numpy().squeeze().astype(np.float32)
                logger.info(f"Synthesized {len(audio)} audio samples for '{text}'")
                return audio
            except Exception as exc:
                logger.error(f"Indic Parler-TTS generation error: {exc}")

        # Lightweight fallback tone if Parler-TTS model generation is unavailable
        logger.info("Using fallback audio generation...")
        duration = max(1.0, len(text) * 0.08)
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)
        return tone.astype(np.float32)

    def play(self, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
        """
        Play audio samples through default speaker output using sounddevice.

        Args:
            audio: Mono float32 NumPy audio array.
            sample_rate: Sample rate in Hz (default 24000 Hz).
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
    tts = TTSService()

    test_sentences = [
        ("en", "Welcome to our campus helpdesk. How can I assist you?"),
        ("hi", "हमारे परिसर सहायता केंद्र में आपका स्वागत है।"),
        ("kn", "ನಮ್ಮ ಕ್ಯಾಂಪಸ್ ಸಹಾಯ ಕೇಂದ್ರಕ್ಕೆ ಸ್ವಾಗತ."),
    ]

    for lang, sentence in test_sentences:
        print(f"\n--- Testing TTS ({lang.upper()}) ---")
        print(f"Sentence: \"{sentence}\"")
        audio_samples = tts.synthesize(sentence, language=lang)
        tts.play(audio_samples, sample_rate=SAMPLE_RATE)
