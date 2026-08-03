"""
assistant_loop.py
Main orchestrator — NO wake word. Flow:

  camera sees a face
       -> speak welcome greeting
       -> mic opens for LISTEN_WINDOW_SECONDS (15-20s)
          - stops EARLY if the person goes silent for SILENCE_CUTOFF seconds
            (so it doesn't always wait the full 20s if they finish talking sooner)
       -> mic closes
       -> audio sent to STT -> (TTT reply) -> TTS speaks the answer
       -> back to idle, watching the camera again

Only one listening session runs at a time; new arrivals are ignored while
a session is already active (guarded by self._busy).

Install:
    pip install opencv-python faster-whisper sounddevice numpy parler-tts
"""

import os
import sys
import time
import warnings
import logging
import threading
import numpy as np
import sounddevice as sd

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("comtypes").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("faiss").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from presence_service import PresenceService
from stt_service import STTService, SAMPLE_RATE
from tts_service import TTSService
from ttt_service import TTTService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("assistant_loop")

# ---- Config ------------------------------------------------------------------
LISTEN_WINDOW_SECONDS = float(os.getenv("LISTEN_WINDOW_SECONDS", "18"))   # hard cap
SILENCE_CUTOFF_SECONDS = float(os.getenv("SILENCE_CUTOFF_SECONDS", "2.5"))  # stop early if quiet this long
SILENCE_RMS_THRESHOLD = float(os.getenv("SILENCE_RMS_THRESHOLD", "0.003"))   # tune to your mic's noise floor
CHUNK_SECONDS = 0.5  # granularity for silence checking


def record_until_silence(max_seconds: float, silence_seconds: float) -> np.ndarray:
    """
    Records from the mic, stopping early if silence_seconds of quiet audio
    is detected, otherwise stopping at max_seconds regardless.
    """
    chunk_frames = int(CHUNK_SECONDS * SAMPLE_RATE)
    max_chunks = int(max_seconds / CHUNK_SECONDS)
    silence_chunks_needed = int(silence_seconds / CHUNK_SECONDS)

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    chunks = []
    silent_run = 0
    speech_started = False

    with stream:
        for _ in range(max_chunks):
            data, _ = stream.read(chunk_frames)
            data = data.flatten()
            chunks.append(data)

            rms = float(np.sqrt(np.mean(data ** 2)))
            logger.debug(f"[MIC RMS] Chunk RMS: {rms:.4f} (threshold: {SILENCE_RMS_THRESHOLD:.4f})")
            if rms > SILENCE_RMS_THRESHOLD:
                speech_started = True
                silent_run = 0
            elif speech_started:
                silent_run += 1
                if silent_run >= silence_chunks_needed:
                    logger.info("Silence detected, ending listening window early.")
                    break

    return np.concatenate(chunks) if chunks else np.array([], dtype="float32")


def speak(text: str, language: str = "en"):
    """Synthesize `text` and play it through speaker using TTSService."""
    logger.info(f'[ASSISTANT SAYS] ({language}): "{text}"')
    tts = TTSService()
    audio = tts.synthesize(text, language=language)
    tts.play(audio)


def generate_reply(user_text: str, language: str = "en") -> str:
    """Generate response text for user input using TTTService."""
    ttt = TTTService()
    return ttt.get_reply(user_text, language=language)


# Unicode block ranges for the scripts we care about.
_DEVANAGARI_RANGE = (0x0900, 0x097F)   # Hindi / Sanskrit
_KANNADA_RANGE    = (0x0C80, 0x0CFF)   # Kannada

_LANG_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}


def _display_text(user_text: str, language: str) -> str:
    """
    Return the text to show on screen / in logs for the user's utterance.

    When Whisper detects a language correctly but produces output in the WRONG
    script (e.g. Kannada speech → Devanagari characters instead of Kannada
    script), the raw transcription looks like garbled nonsense to a human
    reader.  In those cases we substitute a clean placeholder instead of
    printing the confusing raw bytes.

    The raw `user_text` is NOT modified here — it is still passed unchanged to
    TTT for matching, where the cross-script regex safety net handles it.
    """
    def _has_script(text: str, lo: int, hi: int) -> bool:
        return any(lo <= ord(ch) <= hi for ch in text)

    label = _LANG_LABELS.get(language, language.upper())

    if language == "kn":
        # Devanagari in output but no Kannada script → wrong-script transcription
        if _has_script(user_text, *_DEVANAGARI_RANGE) and \
           not _has_script(user_text, *_KANNADA_RANGE):
            return f"[Recognized: {label} speech]"

    if language == "hi":
        # Kannada script in output but no Devanagari → wrong-script transcription
        if _has_script(user_text, *_KANNADA_RANGE) and \
           not _has_script(user_text, *_DEVANAGARI_RANGE):
            return f"[Recognized: {label} speech]"

    return user_text


class AssistantLoop:
    def __init__(self):
        self.stt = STTService()
        self.tts = TTSService()
        self.ttt = TTTService()
        self._busy = False
        self._lock = threading.Lock()
        self.presence = PresenceService(
            on_person_arrived=self._on_person_arrived,
            on_person_left=self._on_person_left,
        )

    def _on_person_arrived(self):
        with self._lock:
            if self._busy:
                logger.info("New person arrived while assistant is busy in active conversation. Ignoring re-entrant trigger.")
                return
            self._busy = True
        threading.Thread(target=self._run_session, daemon=True).start()

    def _on_person_left(self):
        logger.info("Person left the frame.")

    def _run_session(self):
        try:
            speak("Hi there! Go ahead, I'm listening.", language="en")

            logger.info(f"Listening for up to {LISTEN_WINDOW_SECONDS}s...")
            audio = record_until_silence(LISTEN_WINDOW_SECONDS, SILENCE_CUTOFF_SECONDS)

            if len(audio) == 0:
                speak("I didn't hear anything.", language="en")
                return

            result = self.stt.transcribe_audio(audio)
            user_text = result["text"]
            language = result.get("language") or "en"

            if not user_text:
                speak("Sorry, I couldn't understand that.", language=language)
                return

            logger.info(f"Heard ({language}): {_display_text(user_text, language)}")
            reply = generate_reply(user_text, language=language)
            speak(reply, language=language)

        finally:
            with self._lock:
                self._busy = False

    def _warmup_ollama(self, max_retries: int = 5, backoff_factor: float = 1.5):
        """Warm up Ollama VRAM with retry-with-backoff for systemd boot sequence resiliency."""
        logger.info("Warming up Ollama model (with retry-with-backoff)...")
        wait_time = 1.0
        
        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                llm = None
                if self.ttt.rag_service:
                    llm = getattr(self.ttt.rag_service, "_llm_service", getattr(self.ttt.rag_service, "llm_service", None))
                
                if llm is not None:
                    llm.generate("hello")
                else:
                    from campus_helpdesk.config.settings import get_settings
                    from ollama import Client
                    settings = get_settings()
                    client = Client(host=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds)
                    client.chat(
                        model=settings.ollama_model,
                        messages=[{"role": "user", "content": "hello"}],
                        options={"num_predict": 1},
                    )
                elapsed = time.time() - start_time
                logger.info(f"Ollama warm-up succeeded on attempt {attempt}/{max_retries} in {elapsed:.2f}s.")
                return True
            except Exception as e:
                logger.warning(f"Ollama warm-up attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying Ollama warm-up in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
                else:
                    logger.warning(f"All {max_retries} Ollama warm-up attempts exhausted. Assistant starting in graceful offline mode.")
                    return False

    def start(self):
        self._warmup_ollama()
        self.presence.start()
        logger.info("Assistant running. Waiting for someone to appear on camera...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.presence.stop()
            logger.info("Assistant stopped.")


if __name__ == "__main__":
    AssistantLoop().start()
