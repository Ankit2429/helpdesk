"""
test_latency_session.py
Runs the exact same query 5 times in a row in a single process session
to analyze Ollama initial model loading warm-up latency vs subsequent query execution speed.
"""

import os
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OLLAMA_NUM_GPU"] = "0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ttt_service import TTTService


def main():
    print("\n=======================================================================")
    print("      SINGLE-SESSION 5-CALL LATENCY WARM-UP & STABILITY TEST")
    print("=======================================================================")
    print("  Model Target : qwen2.5:1.5b (100% Forced CPU Execution)")
    print("  Test Query   : \"Where is the library located in campus?\"")
    print("=======================================================================\n")

    t_init = time.time()
    service = TTTService()
    init_duration = time.time() - t_init
    print(f"Service Initialization Duration: {init_duration:.2f} s\n")

    query = "Where is the library located in campus?"
    latencies = []

    for i in range(1, 6):
        print(f">>> Execution Call #{i}:")
        t0 = time.time()
        reply = service.get_reply(query, language="en")
        elapsed = time.time() - t0
        latencies.append(elapsed)
        print(f"    Answer  : \"{reply}\"")
        print(f"    Latency : {elapsed:.2f} s\n")

    print("=" * 70)
    print("LATENCY ANALYSIS TABLE:")
    print("=" * 70)
    print(f"{'Call #':<8} | {'Latency (sec)':<15} | {'Phase / Type'}")
    print("-" * 70)
    for idx, lat in enumerate(latencies, 1):
        phase = "Warm-up / First Load (Initial Model Loading into Memory)" if idx == 1 else "Warmed Memory Execution"
        print(f"Call #{idx:<3} | {lat:.2f} s           | {phase}")

    print("=" * 70)
    first_call = latencies[0]
    subsequent_avg = sum(latencies[1:]) / len(latencies[1:])
    print(f"First Call Latency          : {first_call:.2f} s")
    print(f"Subsequent Calls Average    : {subsequent_avg:.2f} s")
    print(f"Speedup Factor After Warmup : {first_call / subsequent_avg:.1f}x faster")
    print("=" * 70)

    if first_call > 2.0 * subsequent_avg:
        print("VERDICT: Predictable initial model load spike! The first query in a session incurs Ollama model-loading into RAM, after which subsequent queries execute consistently fast.")
    else:
        print("VERDICT: Uniform latency across all calls.")


if __name__ == "__main__":
    main()
