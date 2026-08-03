"""Raspberry Pi Benchmark Script 1: Ollama qwen2.5:3b Active Generation RAM Footprint."""

import sys
import time
import threading
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Error: psutil is required. Run 'pip install psutil' on your Pi.")
    sys.exit(1)

try:
    import ollama
except ImportError:
    print("Error: ollama python package is required. Run 'pip install ollama' on your Pi.")
    sys.exit(1)

MODEL_NAME = "qwen2.5:3b"

def get_ram_mb() -> float:
    """Return currently used system RAM in Megabytes."""
    return psutil.virtual_memory().used / (1024 * 1024)

def main():
    print("\n" + "=" * 70)
    print(f"      RASPBERRY PI BENCHMARK: {MODEL_NAME} ACTIVE GENERATION RAM")
    print("=" * 70 + "\n")

    vm = psutil.virtual_memory()
    total_ram_gb = vm.total / (1024 ** 3)
    baseline_ram_mb = vm.used / (1024 ** 2)

    print(f"System Total RAM: {total_ram_gb:.2f} GB")
    print(f"Baseline System RAM (Before Loading Model): {baseline_ram_mb:.1f} MB ({vm.percent}%)")

    client = ollama.Client()

    # Verify model is available
    models_list = [m.model for m in client.list().models]
    print(f"\nOllama Local Models: {models_list}")

    prompt = (
        "Write a detailed 400-word official overview of KLE Technological University, "
        "including its engineering departments, campus history, research centers, and academic excellence."
    )

    print(f"\nTriggering active generation on {MODEL_NAME}...")

    peak_ram_mb = baseline_ram_mb
    stop_monitoring = False

    def monitor_ram():
        nonlocal peak_ram_mb
        while not stop_monitoring:
            current_used = psutil.virtual_memory().used / (1024 ** 2)
            if current_used > peak_ram_mb:
                peak_ram_mb = current_used
            time.sleep(0.05)  # Sample every 50ms

    monitor_thread = threading.Thread(target=monitor_ram, daemon=True)
    monitor_thread.start()

    start_time = time.time()
    response = client.generate(model=MODEL_NAME, prompt=prompt)
    elapsed = time.time() - start_time

    stop_monitoring = True
    monitor_thread.join()

    final_ram_mb = psutil.virtual_memory().used / (1024 ** 2)
    net_llm_ram_mb = peak_ram_mb - baseline_ram_mb
    tokens_generated = len(response.response.split())
    tps = tokens_generated / elapsed if elapsed > 0 else 0

    print("\n" + "-" * 70)
    print("                 BENCHMARK RESULTS")
    print("-" * 70)
    print(f"Model Evaluated                   : {MODEL_NAME}")
    print(f"Baseline System RAM               : {baseline_ram_mb:.1f} MB")
    print(f"Peak System RAM During Generation : {peak_ram_mb:.1f} MB")
    print(f"Net LLM Memory Footprint         : {net_llm_ram_mb:.1f} MB ({net_llm_ram_mb/1024:.2f} GB)")
    print(f"Generation Latency                : {elapsed:.2f} seconds ({tps:.1f} approx words/s)")
    print("-" * 70)
    print(f"8GB Raspberry Pi Headroom         : {(8192 - peak_ram_mb):.1f} MB remaining")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
