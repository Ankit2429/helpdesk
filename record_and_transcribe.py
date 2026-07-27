"""
record_and_transcribe.py
Real microphone recording + Whisper STT with candidate-list language detection.
Prints a 3-second countdown before recording so you can get ready.
No simulation, no pre-recorded audio.
"""
import io, sys, time
# Force UTF-8 output so non-ASCII transcriptions don't crash on Windows cp1252
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pyaudio

SAMPLE_RATE    = 16000
CHANNELS       = 1
CHUNK          = 1024
RECORD_SECONDS = 7   # enough time for a full question


def countdown(n: int):
    for i in range(n, 0, -1):
        print(f"  Starting in {i}...", flush=True)
        time.sleep(1)


def record_from_mic() -> np.ndarray:
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print()
    print("=" * 60)
    print("  GET READY TO SPEAK — countdown starting...")
    print("=" * 60)
    countdown(3)
    print()
    print("  >>> RECORDING NOW — speak your question <<<")
    print(f"  (recording for {RECORD_SECONDS} seconds...)")
    print(flush=True)

    frames = []
    for _ in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    pa.terminate()

    print()
    print("  Recording complete. Running language detection + transcription...")
    print(flush=True)

    raw = b"".join(frames)
    audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return audio_np


def transcribe(audio_np: np.ndarray) -> dict:
    from stt_service import STTService
    stt = STTService()
    return stt.transcribe_audio(audio_np, vad_filter=False)


if __name__ == "__main__":
    audio = record_from_mic()
    result = transcribe(audio)

    text = result.get("text", "").strip()
    lang = result.get("language", "unknown")
    conf = result.get("language_probability", 0.0)

    print()
    print("=" * 60)
    print(f'  RAW STT TRANSCRIPTION : "{text}"')
    print(f'  DETECTED LANGUAGE     : "{lang}" (confidence {conf:.2f})')
    print("=" * 60)
    print(flush=True)

    if not text:
        print("\n[WARN] Transcription is empty — mic may have recorded silence.")
        sys.exit(1)
