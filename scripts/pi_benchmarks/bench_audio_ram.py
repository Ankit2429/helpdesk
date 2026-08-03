"""Raspberry Pi Benchmark Script 2: FasterWhisper Small + Piper TTS Combined Memory Footprint."""

import sys
import time
import wave
import threading
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    import psutil
except ImportError:
    print("Error: psutil is required. Run 'pip install psutil' on your Pi.")
    sys.exit(1)

from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService

def generate_test_pcm() -> bytes:
    """Generate 5 seconds of 16kHz 16-bit PCM audio."""
    sample_rate = 16000
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    signal = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
    return signal.tobytes()

def main():
    print("\n" + "=" * 70)
    print("      RASPBERRY PI BENCHMARK: WHISPER SMALL + PIPER TTS RAM")
    print("=" * 70 + "\n")

    vm = psutil.virtual_memory()
    baseline_ram_mb = vm.used / (1024 ** 2)
    print(f"Baseline System RAM: {baseline_ram_mb:.1f} MB")

    peak_ram_mb = baseline_ram_mb
    stop_monitoring = False

    def monitor_ram():
        nonlocal peak_ram_mb
        while not stop_monitoring:
            current_used = psutil.virtual_memory().used / (1024 ** 2)
            if current_used > peak_ram_mb:
                peak_ram_mb = current_used
            time.sleep(0.05)

    monitor_thread = threading.Thread(target=monitor_ram, daemon=True)
    monitor_thread.start()

    print("\n[1/2] Loading FasterWhisper 'small' (int8 quantization)...")
    stt_service = FasterWhisperSTTService(model_size="small", device="cpu", compute_type="int8")
    after_stt_ram_mb = psutil.virtual_memory().used / (1024 ** 2)

    print("[2/2] Loading Piper ONNX Neural Voice Service...")
    tts_service = NonBlockingTTSService(voice_model="en_US-lessac-medium")
    after_tts_ram_mb = psutil.virtual_memory().used / (1024 ** 2)

    print("\nExecuting simultaneous STT transcription and TTS playback...")
    pcm_bytes = generate_test_pcm()
    
    start_time = time.time()
    # 1. Trigger TTS synthesis
    tts_service.speak("Welcome to KLE Technological University campus helpdesk.", language="en")
    
    # 2. Simultaneously run Whisper STT
    stt_res = stt_service.transcribe_audio(pcm_bytes, sample_rate=16000)
    
    tts_service.wait_until_done(timeout=10.0)
    elapsed = time.time() - start_time

    stop_monitoring = True
    monitor_thread.join()

    print("\n" + "-" * 70)
    print("                 BENCHMARK RESULTS")
    print("-" * 70)
    print(f"Baseline System RAM            : {baseline_ram_mb:.1f} MB")
    print(f"RAM After Loading Whisper Small: {after_stt_ram_mb:.1f} MB (+{after_stt_ram_mb - baseline_ram_mb:.1f} MB)")
    print(f"RAM After Loading Piper TTS    : {after_tts_ram_mb:.1f} MB (+{after_tts_ram_mb - after_stt_ram_mb:.1f} MB)")
    print(f"Peak System RAM During Execution: {peak_ram_mb:.1f} MB")
    print(f"Combined Audio Memory Footprint: {(peak_ram_mb - baseline_ram_mb):.1f} MB ({((peak_ram_mb - baseline_ram_mb)/1024):.2f} GB)")
    print(f"Processing Latency             : {elapsed:.2f} seconds")
    print("-" * 70 + "\n")

if __name__ == "__main__":
    main()
