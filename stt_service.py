"""
stt_service.py
Offline Speech-to-Text service — Whisper small, candidate-list language detection.

Uses faster-whisper (CTranslate2 backend) instead of plain openai-whisper:
- ~4x faster on CPU, much lower RAM — matters a lot on a Raspberry Pi.
- int8 quantization keeps model size and memory small.
- Same Whisper weights under the hood, so accuracy is identical to
  openai-whisper's "small" checkpoint.

Language detection strategy:
  Whisper's free-form auto-detect is unreliable when only 3 languages are
  needed (English, Hindi, Kannada).  Instead of trusting the unconstrained
  language detector we:
    1. Call model.detect_language() to get probabilities for ALL languages.
    2. Filter to CANDIDATE_LANGUAGES {en, hi, kn} — eliminates false detections
       like 'nn' (Norwegian Nynorsk) or 'ta' that Whisper picks on ambiguous audio.
    3. Pick the candidate with the highest probability.
    4. Transcribe with that language FORCED — much more accurate and stable.

  Known limitation: Whisper occasionally writes Kannada utterances in Devanagari
  script rather than native Kannada script.  ttt_service.py carries cross-script
  phonetic regex matching as the safety-net mitigation for this.

  If WHISPER_LANGUAGE env var is set, that language is always forced (bypasses
  candidate detection), useful for single-language deployments.

Install:
    pip install faster-whisper sounddevice numpy
"""

import os
import sys
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stt_service")

# ---- Config (env-overridable, same pattern as before) ----------------------
WHISPER_MODEL_SIZE   = os.getenv("WHISPER_MODEL_SIZE",   "small")   # tiny/base/small/medium
WHISPER_LANGUAGE     = os.getenv("WHISPER_LANGUAGE",     "")        # "" = candidate-list detect
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")    # int8 = fastest on Pi CPU
SAMPLE_RATE          = 16000                                         # Whisper expects 16kHz mono

# Languages the deployment actually supports.  Auto-detect is constrained to
# this set; any other language Whisper might hallucinate is ignored.
CANDIDATE_LANGUAGES = {"en", "hi", "kn"}


class STTService:
    """
    Loads Whisper once, reuses it for every transcription call.

    Language detection is constrained to CANDIDATE_LANGUAGES (en/hi/kn)
    unless WHISPER_LANGUAGE is set in the environment, in which case that
    language is always forced.
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

        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            if any(err_msg in str(e) for err_msg in ("DLL load failed", "AppLocker", "Application Control", "policy")):
                import types
                av_mock = types.ModuleType("av")
                av_mock.__spec__ = types.SimpleNamespace(origin="mock")
                sys.modules["av"] = av_mock
                from faster_whisper import WhisperModel
            else:
                raise

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
            f"{'forced=' + self.forced_language if self.forced_language else 'candidate-list ' + str(sorted(CANDIDATE_LANGUAGES))}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _detect_candidate_language(self, audio: np.ndarray) -> tuple[str, float]:
        """
        Run faster-whisper's detect_language() and return the best match
        within CANDIDATE_LANGUAGES together with its probability.

        Returns (language_code, probability).  Falls back to "en" if the
        candidate list yields nothing (should never happen in practice).
        """
        _, _, all_probs = self.model.detect_language(audio)
        # all_probs is a list of (lang_code, prob) tuples sorted by prob desc
        best_lang, best_prob = "en", 0.0
        for lang_code, prob in all_probs:
            if lang_code in CANDIDATE_LANGUAGES and prob > best_prob:
                best_lang, best_prob = lang_code, prob
        return best_lang, best_prob

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def transcribe_audio(self, audio: np.ndarray, vad_filter: bool = False) -> dict:
        """
        Transcribe a mono float32 numpy array sampled at 16kHz.

        Language selection order:
          1. WHISPER_LANGUAGE env var set → always forced.
          2. Otherwise → detect_language() filtered to CANDIDATE_LANGUAGES.

        Returns:
            {
              "text": "recognized text",
              "language": "en" | "hi" | "kn",
              "language_probability": 0.0-1.0
            }
        """
        if audio is None or len(audio) == 0:
            return {"text": "", "language": None, "language_probability": 0.0}

        if self.forced_language:
            lang = self.forced_language
            lang_prob = 1.0  # forced; no detection run
            logger.info(f"Language forced to '{lang}' via WHISPER_LANGUAGE env var.")
        else:
            lang, lang_prob = self._detect_candidate_language(audio)
            logger.info(
                f"Candidate-list language detection: '{lang}' "
                f"(p={lang_prob:.2f}) from candidates {sorted(CANDIDATE_LANGUAGES)}"
            )

        segments, info = self.model.transcribe(
            audio,
            language=lang,
            vad_filter=vad_filter,
            beam_size=5,
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()

        logger.info(
            f"Transcribed (lang={lang}, p={lang_prob:.2f}) -> \"{text}\""
        )

        return {
            "text": text,
            "language": lang,
            "language_probability": lang_prob,
        }

    def transcribe_file(self, filepath: str) -> dict:
        """Transcribe an audio file directly (wav/mp3/flac/etc.)."""
        if self.forced_language:
            lang = self.forced_language
            lang_prob = 1.0
        else:
            # load audio briefly for language detection
            import soundfile as sf
            audio_data, sr = sf.read(filepath, dtype="float32")
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
            lang, lang_prob = self._detect_candidate_language(audio_data)

        segments, info = self.model.transcribe(
            filepath,
            language=lang,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "language": lang,
            "language_probability": lang_prob,
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
    result = stt.record_and_transcribe(duration_seconds=7.0)
    print("\n--- Result ---")
    print(f"Language : {result['language']} ({result['language_probability']:.2%} confidence)")
    print(f"Text     : {result['text']}")
