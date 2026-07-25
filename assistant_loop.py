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
import time
import logging
import threading
import numpy as np
import sounddevice as sd

from presence_service import PresenceService
from stt_service import STTService, SAMPLE_RATE
from tts_service import TTSService
from ttt_service import TTTService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("assistant_loop")

# ---- Config ------------------------------------------------------------------
LISTEN_WINDOW_SECONDS = float(os.getenv("LISTEN_WINDOW_SECONDS", "18"))   # hard cap
SILENCE_CUTOFF_SECONDS = float(os.getenv("SILENCE_CUTOFF_SECONDS", "2.5"))  # stop early if quiet this long
SILENCE_RMS_THRESHOLD = float(os.getenv("SILENCE_RMS_THRESHOLD", "0.01"))   # tune to your mic's noise floor
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
            logger.info(f"[MIC RMS] Chunk RMS: {rms:.4f} (threshold: {SILENCE_RMS_THRESHOLD:.4f})")
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

            logger.info(f"Heard ({language}): {user_text}")
            reply = generate_reply(user_text, language=language)
            speak(reply, language=language)

        finally:
            with self._lock:
                self._busy = False

    def start(self):
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
