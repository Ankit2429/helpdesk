"""
test_tts_speed.py
Measures and compares response latency between pre-rendered cached audio (tts_cache/)
and live SDPA-accelerated ParlerTTS neural generation.
"""

import datetime
import logging
import time
from tts_service import TTSService
from ttt_service import TTTService, round_time_to_5_min

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_tts_speed")


def main():
    tts = TTSService()
    ttt = TTTService()

    # 1. Test Pre-rendered Canned Path
    canned_text = "Hello! Welcome to our campus. How can I assist you today?"
    logger.info("=== Testing CACHED CANNED Path ===")
    t0 = time.time()
    canned_audio = tts.synthesize(canned_text, language="en")
    canned_elapsed = time.time() - t0
    logger.info(f"Cached canned synthesis returned in {canned_elapsed * 1000:.2f} ms ({len(canned_audio)} samples)")

    # 2. Test Time Query Path with pre-rendered time (1:00 AM)
    sample_dt = datetime.datetime(2026, 7, 26, 1, 0)
    rounded_time_str = round_time_to_5_min(sample_dt)
    time_text = f"It is currently {rounded_time_str}."
    logger.info(f"\n=== Testing TIME QUERY Path (\"'{time_text}'\") ===")
    t1 = time.time()
    time_audio = tts.synthesize(time_text, language="en")
    time_elapsed = time.time() - t1
    logger.info(f"Time query synthesis returned in {time_elapsed * 1000 if time_elapsed < 1.0 else time_elapsed:.2f} {'ms' if time_elapsed < 1.0 else 'seconds'}")

    print("\n" + "=" * 50)
    print("TTS TIMING PERFORMANCE SUMMARY:")
    print(f"  - Cached Canned Latency : {canned_elapsed * 1000:.2f} ms (INSTANT)")
    if time_elapsed < 1.0:
        print(f"  - Time Query Latency    : {time_elapsed * 1000:.2f} ms (INSTANT CACHED)")
    else:
        print(f"  - Time Query Latency    : {time_elapsed:.2f} seconds (UNCACHED LIVE)")
    print("=" * 50)


if __name__ == "__main__":
    main()
