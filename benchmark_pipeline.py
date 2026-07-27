"""
benchmark_pipeline.py
End-to-End Pipeline Benchmark for Production Architecture (Pi-Target):
- STT: faster-whisper small (int8 CPU)
- TTT: Fast Intent Pre-Check + RAG (FAISS + Ollama llama3.2:3b)
- TTS: Tier 1 WAV Cache + Tier 2 Meta MMS-TTS (HI/KN) & Piper (EN)
"""

import logging
import os
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OLLAMA_NUM_GPU"] = "0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark")

from ttt_service import TTTService
from tts_service import TTSService, SAMPLE_RATE


def main():
    print("\n" + "=" * 65)
    print("      PRODUCTION RASPBERRY PI ARCHITECTURE PIPELINE BENCHMARK")
    print("=" * 65)
    print("  - STT : faster-whisper small int8 CPU")
    print("  - TTT : Fast Intent Pre-Check -> FAISS + Ollama (llama3.2:3b)")
    print("  - TTS : Tier 1 Cache (~1ms) + Tier 2 CPU (Piper EN / Meta MMS HI, KN)")
    print("=" * 65 + "\n")

    ttt = TTTService()
    tts = TTSService()

    benchmark_queries = [
        ("en", "hello", "Fast Canned Greeting (EN)"),
        ("en", "what time is it", "Fast Canned Time (EN)"),
        ("en", "Where is the library located in campus?", "Open-Ended Campus RAG Query (EN)"),
        ("hi", "पुस्तकालय की जानकारी दें", "Open-Ended Campus RAG Query (HI)"),
        ("kn", "ಕ್ಯಾಂಪಸ್ ಸಹಾಯ ಕೇಂದ್ರ ಎಲ್ಲಿದೆ?", "Open-Ended Campus RAG Query (KN)"),
    ]

    results = []

    for lang, query, category in benchmark_queries:
        print(f"\n>>> Running Benchmark: [{category}] ({lang.upper()})")
        print(f"    Query: \"{query}\"")

        # 1. TTT / RAG Stage
        t_ttt_start = time.time()
        reply_text = ttt.get_reply(query, language=lang)
        ttt_latency = time.time() - t_ttt_start

        # 2. TTS Synthesis Stage
        t_tts_start = time.time()
        audio_samples = tts.synthesize(reply_text, language=lang)
        tts_latency = time.time() - t_tts_start

        total_latency = ttt_latency + tts_latency

        results.append({
            "category": category,
            "lang": lang,
            "query": query,
            "reply": reply_text,
            "ttt_sec": ttt_latency,
            "tts_sec": tts_latency,
            "total_sec": total_latency,
            "samples": len(audio_samples),
        })

        print(f"    Answer: \"{reply_text}\"")
        print(f"    TTT / RAG Latency : {ttt_latency:.2f} s")
        print(f"    TTS Latency       : {tts_latency * 1000 if tts_latency < 1.0 else tts_latency:.2f} {'ms' if tts_latency < 1.0 else 's'}")
        print(f"    Total Processing  : {total_latency:.2f} s")

    print("\n" + "=" * 70)
    print("                 FINAL BENCHMARK PERFORMANCE REPORT")
    print("=" * 70)
    print(f"{'Category':<35} | {'TTT / RAG':<10} | {'TTS Latency':<12} | {'Total Latency'}")
    print("-" * 70)
    for r in results:
        tts_str = f"{r['tts_sec']*1000:.1f} ms" if r['tts_sec'] < 1.0 else f"{r['tts_sec']:.2f} s"
        print(f"{r['category']:<35} | {r['ttt_sec']:<9.2f}s | {tts_str:<12} | {r['total_sec']:.2f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
