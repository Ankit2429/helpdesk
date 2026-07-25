"""
stt_service.py
Offline Speech-to-Text service — Whisper small, auto language detection.

Uses faster-whisper (CTranslate2 backend) instead of plain openai-whisper:
- ~4x faster on CPU, much lower RAM — matters a lot on a Raspberry Pi.
- int8 quantization keeps model size and memory small.
- Same Whisper weights under the hood, so accuracy is identical to
  openai-whisper's "small" checkpoint.

Install:
    pip install faster-whisper sounddevice numpy
"""

import os
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stt_service")

# ---- Config (env-overridable, same pattern as before) ----------------------
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")   # tiny/base/small/medium
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "")            # "" = auto-detect
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8 = fastest on Pi CPU
SAMPLE_RATE = 16000                                              # Whisper expects 16kHz mono


class STTService:
    """
    Loads Whisper once, reuses it for every transcription call.
    Language is auto-detected per utterance unless WHISPER_LANGUAGE is set.
    """

    _instance = None  # simple singleton so the model loads only once per process

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        from faster_whisper import WhisperModel

        logger.info(
            f"Loading Whisper model='{WHISPER_MODEL_SIZE}' "
            f"compute_type='{WHISPER_COMPUTE_TYPE}' (this happens once)..."
        )
        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        self.forced_language = WHISPER_LANGUAGE or None
        logger.info(
            f"Whisper ready. Language mode: "
            f"{'auto-detect' if self.forced_language is None else self.forced_language}"
        )

    def transcribe_audio(self, audio: np.ndarray) -> dict:
        """
        Transcribe a mono float32 numpy array sampled at 16kHz.

        Returns:
            {
              "text": "recognized text",
              "language": "en" | "hi" | "kn" | ...,
              "language_probability": 0.0-1.0
            }
        """
        if audio is None or len(audio) == 0:
            return {"text": "", "language": None, "language_probability": 0.0}

        segments, info = self.model.transcribe(
            audio,
            language=self.forced_language,   # None -> auto-detect
            vad_filter=True,                 # trims silence, helps accuracy + speed
            beam_size=5,
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()

        logger.info(
            f"Detected language={info.language} "
            f"(p={info.language_probability:.2f}) -> \"{text}\""
        )

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
        }

    def transcribe_file(self, filepath: str) -> dict:
        """Transcribe an audio file directly (wav/mp3/flac/etc.)."""
        segments, info = self.model.transcribe(
            filepath,
            language=self.forced_language,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
        }

    def record_and_transcribe(self, duration_seconds: float = 5.0) -> dict:
        """
        Record `duration_seconds` of audio from the default mic and transcribe it.
        Useful for testing; the real assistant loop will instead pass in audio
        captured after wake-word detection (see assistant_loop.py).
        """
        import sounddevice as sd

        logger.info(f"Recording for {duration_seconds}s...")
        audio = sd.rec(
            int(duration_seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = audio.flatten()
        logger.info("Recording done, transcribing...")
        return self.transcribe_audio(audio)


# ---- Quick manual test -------------------------------------------------------
if __name__ == "__main__":
    stt = STTService()
    result = stt.record_and_transcribe(duration_seconds=5.0)
    print("\n--- Result ---")
    print(f"Language : {result['language']} ({result['language_probability']:.2%} confidence)")
    print(f"Text     : {result['text']}")
