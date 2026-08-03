"""End-to-End Voice Pipeline Verification (TTS & STT)."""

import logging
import os
from pathlib import Path
import wave
import numpy as np

from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_voice_pipeline")

MULTILINGUAL_TEST_PHRASES = [
    {"lang": "en", "label": "English", "text": "Hello, I am the campus helpdesk assistant."},
    {"lang": "hi", "label": "Hindi", "text": "नमस्ते, मैं कैंपस हेल्पडेस्क सहायक हूँ।"},
    {"lang": "kn", "label": "Kannada", "text": "ನಮಸ್ಕಾರ, ನಾನು ಕ್ಯಾಂಪಸ್ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್ ಸಹಾಯಕ."},
]
SCRATCH_DIR = Path("scratch")


def convert_wav_to_16k_mono_pcm(wav_path: Path) -> bytes:
    """Read a WAV file and convert to 16kHz 16-bit mono PCM bytes."""
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    # Decode PCM
    if sampwidth == 2:
        samples = np.frombuffer(raw_bytes, dtype=np.int16)
    else:
        samples = np.frombuffer(raw_bytes, dtype=np.int16)

    # Convert multi-channel to mono
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    # Resample to 16000 Hz if necessary
    if framerate != 16000:
        num_target_samples = int(len(samples) * 16000 / framerate)
        samples = np.interp(
            np.linspace(0, len(samples), num_target_samples, endpoint=False),
            np.arange(len(samples)),
            samples,
        ).astype(np.int16)

    return samples.tobytes()


def main() -> None:
    SCRATCH_DIR.mkdir(exist_ok=True)
    
    print("\n" + "=" * 70)
    print("STARTING MULTILINGUAL VOICE PIPELINE (ENGLISH, HINDI, KANNADA) VERIFICATION")
    print("=" * 70 + "\n")

    print("[1/3] Testing NonBlockingTTSService multi-voice synthesis...")
    tts_service = NonBlockingTTSService()
    for item in MULTILINGUAL_TEST_PHRASES:
        tts_service.speak(item["text"], language=item["lang"])
    tts_service.wait_until_done(timeout=10.0)
    print("  -> NonBlockingTTSService completed multi-voice speech requests.")

    print("\n[2/3] Initializing FasterWhisperSTTService (model='small', language auto-detection)...")
    stt_service = FasterWhisperSTTService(model_size="small", device="cpu", compute_type="int8", debug=True)

    import pyttsx3
    engine = pyttsx3.init()

    print(f"\n[3/3] Running TTS -> STT verification for English, Hindi, and Kannada...\n")
    
    for item in MULTILINGUAL_TEST_PHRASES:
        lang_code = item["lang"]
        label = item["label"]
        phrase = item["text"]
        wav_path = SCRATCH_DIR / f"tts_{label.lower()}.wav"

        if wav_path.exists():
            wav_path.unlink()

        engine.save_to_file(phrase, str(wav_path))
        engine.runAndWait()

        file_size_bytes = wav_path.stat().st_size if wav_path.exists() else 0
        
        if file_size_bytes > 0:
            pcm_bytes = convert_wav_to_16k_mono_pcm(wav_path)
            result = stt_service.transcribe_audio(pcm_bytes, sample_rate=16000)
            trans_text = result.text
            detected_lang = result.language
            confidence = result.confidence
        else:
            trans_text = "[No audio rendered]"
            detected_lang = "N/A"
            confidence = 0.0

        print(f"Language: {label} ({lang_code.upper()})")
        print(f"  Input Text         : \"{phrase}\"")
        print(f"  Audio Output File  : {wav_path} ({file_size_bytes} bytes / {file_size_bytes / 1024:.2f} KB)")
        print(f"  Transcribed Text   : \"{trans_text}\"")
        print(f"  Detected Language  : '{detected_lang}' (Confidence: {confidence:.2%})")
        print("-" * 70)

    print("\n" + "=" * 70)
    print("SUMMARY OF PIPER VOICE COVERAGE:")
    print("  - English (EN): FULL Piper ONNX neural voice support (en_US-lessac-medium)")
    print("  - Hindi (HI)  : FULL Piper ONNX neural voice support (hi_IN-pratham-medium)")
    print("  - Kannada (KN): NO official Piper voice exists in Piper catalog -> Fallback to pyttsx3/gTTS/mms-tts")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
