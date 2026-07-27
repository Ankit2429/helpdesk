"""
precache_tts.py
Pre-renders all fixed canned reply strings AND 5-minute time increment responses across 12 hours
(for English, Hindi, and Kannada) into 24kHz WAV audio files stored in tts_cache/.
"""

import hashlib
import logging
import os
import re
import time
import wave
import numpy as np

from tts_service import TTSService, SAMPLE_RATE
from ttt_service import TTTService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precache_tts")

CACHE_DIR = "tts_cache"


def get_cache_filename(text: str, language: str = "en") -> str:
    """Generate a clean deterministic cache filename for text + language."""
    clean_text = text.strip().lower()
    slug = re.sub(r"[^\w]+", "_", clean_text)[:30].strip("_")
    text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:8]
    filename = f"{language}_{slug}_{text_hash}.wav"
    return os.path.join(CACHE_DIR, filename)


def save_wav(filepath: str, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Save 1D float32 numpy audio array as 16-bit mono WAV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


def generate_time_phrases():
    """Generate all 5-minute time increment phrases across 12 hours for EN, HI, KN."""
    phrases = []
    minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    periods = ["AM", "PM"]

    for hour in range(1, 13):
        for minute in minutes:
            for period in periods:
                time_str = f"{hour}:{minute:02d} {period}"
                
                # English
                phrases.append(("en", f"It is currently {time_str}."))
                # Hindi
                phrases.append(("hi", f"अभी समय {time_str} है।"))
                # Kannada
                phrases.append(("kn", f"ಈಗ ಸಮಯ {time_str} ಆಗಿದೆ."))

    return phrases


def main():
    logger.info("Initializing TTS Service for Extended Pre-Caching...")
    tts = TTSService()
    ttt = TTTService()

    # 1. Fixed canned phrases
    canned_phrases = [
        ("en", ttt._handle_greeting("hello", "en")),
        ("hi", ttt._handle_greeting("hello", "hi")),
        ("kn", ttt._handle_greeting("hello", "kn")),
        ("en", ttt._handle_weather("weather", "en")),
        ("hi", ttt._handle_weather("weather", "hi")),
        ("kn", ttt._handle_weather("weather", "kn")),
        ("en", ttt._handle_capabilities("help", "en")),
        ("hi", ttt._handle_capabilities("help", "hi")),
        ("kn", ttt._handle_capabilities("help", "kn")),
        ("en", "Hi there! Go ahead, I'm listening."),
        ("en", "I didn't hear anything."),
        ("en", "Sorry, I couldn't understand that."),
    ]

    # 2. Add 5-minute time increment phrases (288 * 3 = 864 phrases)
    time_phrases = generate_time_phrases()
    all_phrases = canned_phrases + time_phrases

    logger.info(f"Total phrases to check/pre-render: {len(all_phrases)} ({len(canned_phrases)} canned + {len(time_phrases)} time phrases)")
    
    start_time = time.time()
    generated_count = 0
    skipped_count = 0

    for idx, (lang, text) in enumerate(all_phrases, start=1):
        filepath = get_cache_filename(text, language=lang)
        
        # Skip if already pre-rendered
        if os.path.exists(filepath):
            skipped_count += 1
            continue

        logger.info(f"[{idx}/{len(all_phrases)}] Pre-rendering ({lang}): \"{text}\"...")
        item_start = time.time()
        
        audio = tts.synthesize(text, language=lang)
        save_wav(filepath, audio, sample_rate=SAMPLE_RATE)
        
        item_elapsed = time.time() - item_start
        generated_count += 1
        logger.info(f"  -> Saved {filepath} ({len(audio)} samples, {item_elapsed:.2f}s)")

    total_elapsed = time.time() - start_time
    logger.info(f"\n==========================================")
    logger.info(f"EXTENDED PRE-CACHING BATCH SUMMARY:")
    logger.info(f"Total phrases in set : {len(all_phrases)}")
    logger.info(f"New phrases rendered : {generated_count}")
    logger.info(f"Already cached       : {skipped_count}")
    logger.info(f"Total batch duration : {total_elapsed:.2f} seconds")
    logger.info(f"Cache directory      : {os.path.abspath(CACHE_DIR)}")
    logger.info(f"==========================================")


if __name__ == "__main__":
    main()
