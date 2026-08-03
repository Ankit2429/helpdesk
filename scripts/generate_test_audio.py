"""Generate audio files for technical quality comparison (EN, HI, KN)."""

from pathlib import Path
import wave
import pyttsx3
from piper.voice import PiperVoice

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

SAMPLES = [
    {
        "filename": "full_pipeline_en_q1.wav",
        "lang": "en",
        "text": "The annual fee for B.E. programs is 1,12,410 under the KCET quota, 2,28,000 to 3,04,100 under COMEDK, and 1,47,000 to 4,00,000 under Management quota.",
        "piper_model": "data/piper/en_US-lessac-medium.onnx",
        "piper_json": "data/piper/en_US-lessac-medium.onnx.json",
    },
    {
        "filename": "full_pipeline_hi_q2.wav",
        "lang": "hi",
        "text": "बी.ई. (इंजीनियरिंग) पाठ्यक्रमों का वार्षिक शुल्क केसीईटी कोटा के तहत ₹1,12,410, कॉमेडके कोटा के तहत ₹2,28,000 से ₹3,04,100 है।",
        "piper_model": "data/piper/hi_IN-pratham-medium.onnx",
        "piper_json": "data/piper/hi_IN-pratham-medium.onnx.json",
    },
    {
        "filename": "full_pipeline_kn_q3.wav",
        "lang": "kn",
        "text": "ಬಿಸಿಎ ಕೋರ್ಸ್‌ಗೆ ಸೇರಲು ಅಭ್ಯರ್ಥಿಗಳು 10+2 ಅಥವಾ ತತ್ಸಮಾನ ಪರೀಕ್ಷೆಯಲ್ಲಿ ಕನಿಷ್ಠ 45% (ಎಸ್ಸಿ/ಎಸ್ಟಿ ಅಭ್ಯರ್ಥಿಗಳಿಗೆ 40%) ಅಂಕಗಳೊಂದಿಗೆ ಉತ್ತೀರ್ಣರಾಗಿರಬೇಕು.",
        "piper_model": None,
        "piper_json": None,
    },
]

for s in SAMPLES:
    out_path = OUTPUTS_DIR / s["filename"]
    if out_path.exists():
        out_path.unlink()

    if s["piper_model"] and Path(s["piper_model"]).exists():
        print(f"Synthesizing {s['filename']} via Piper ONNX ({s['lang']})...")
        voice = PiperVoice.load(s["piper_model"], config_path=s["piper_json"])
        with wave.open(str(out_path), "wb") as wav_file:
            voice.synthesize_wav(s["text"], wav_file)
        print(f"Saved {s['filename']} ({out_path.stat().st_size} bytes)")
    else:
        print(f"Synthesizing {s['filename']} via pyttsx3 fallback ({s['lang']})...")
        engine = pyttsx3.init()
        engine.save_to_file(s["text"], str(out_path))
        engine.runAndWait()
        engine.stop()
        print(f"Saved {s['filename']} ({out_path.stat().st_size} bytes)")

print("\nAll audio files generated successfully!")
