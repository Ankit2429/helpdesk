"""Raspberry Pi Benchmark Script 3: FULL Stack Peak RAM Footprint Measurement.

Measures combined multi-process Resident Set Size (RSS) RAM usage of:
1. Main Python Application Process (RAG, FAISS Vector Index, Audio STT/TTS)
2. External Ollama Service & LLM Server Daemon processes (ollama.exe, llama-server.exe, ollama_llama_server)
"""

import gc
import sys
import time
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

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.application.rag_chat_service import RAGChatService

def generate_test_pcm() -> bytes:
    """Generate 4 seconds of 16kHz 16-bit PCM audio."""
    sample_rate = 16000
    duration = 4.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    signal = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
    return signal.tobytes()

def get_python_rss_mb() -> float:
    """Get current Python process RSS memory in MB after garbage collection."""
    gc.collect()
    time.sleep(0.05)
    return psutil.Process().memory_info().rss / (1024 ** 2)

def get_ollama_rss_mb() -> float:
    """Find and sum RSS of all running Ollama daemon / runner processes."""
    total_rss_bytes = 0
    keywords = ["ollama", "llama-server", "ollama_llama_server", "runner"]
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name'].lower()
            if any(k in name for k in keywords):
                total_rss_bytes += proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total_rss_bytes / (1024 ** 2)

def main():
    print("\n" + "=" * 76)
    print("   RASPBERRY PI BENCHMARK: FULL STACK COMBINED MULTI-PROCESS PEAK RAM")
    print("======================================================================\n")

    settings = get_settings()

    vm = psutil.virtual_memory()
    total_ram_gb = vm.total / (1024 ** 3)
    
    python_start_rss = get_python_rss_mb()
    ollama_start_rss = get_ollama_rss_mb()
    combined_start_rss = python_start_rss + ollama_start_rss

    print(f"System Physical Total RAM : {total_ram_gb:.2f} GB")
    print(f"Python App Baseline RSS   : {python_start_rss:.1f} MB")
    print(f"Ollama Daemon Baseline RSS: {ollama_start_rss:.1f} MB")
    print(f"Combined Stack Baseline   : {combined_start_rss:.1f} MB")

    peak_python_rss = python_start_rss
    peak_ollama_rss = ollama_start_rss
    peak_combined_rss = combined_start_rss
    stop_monitoring = False
    proc = psutil.Process()

    def monitor_rss():
        nonlocal peak_python_rss, peak_ollama_rss, peak_combined_rss
        while not stop_monitoring:
            try:
                py_rss = proc.memory_info().rss / (1024 ** 2)
                ol_rss = get_ollama_rss_mb()
                comb = py_rss + ol_rss

                if py_rss > peak_python_rss:
                    peak_python_rss = py_rss
                if ol_rss > peak_ollama_rss:
                    peak_ollama_rss = ol_rss
                if comb > peak_combined_rss:
                    peak_combined_rss = comb
            except Exception:
                pass
            time.sleep(0.05)  # 50ms sampling

    monitor_thread = threading.Thread(target=monitor_rss, daemon=True)
    monitor_thread.start()

    # 1. Initialize RAG & FAISS Store
    print("\n[1/4] Loading FAISS Vector Index & Hybrid Retriever...")
    rag_pipeline = create_rag_pipeline(settings)
    rag_pipeline.load_index()
    context_composer = ContextComposer(settings)
    after_rag_py_rss = get_python_rss_mb()

    # 2. Initialize LLM Service
    print(f"[2/4] Initializing LLM Service...")
    llm_service = create_llm_service(settings)
    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        context_composer=context_composer,
    )

    # 3. Initialize STT & TTS Audio Stack
    print("[3/4] Initializing Audio Stack (FasterWhisper Small + Piper ONNX)...")
    stt_service = FasterWhisperSTTService(
        model_size=getattr(settings, "whisper_model_size", "small"),
        device=getattr(settings, "whisper_device", "cpu"),
        compute_type=getattr(settings, "whisper_compute_type", "int8"),
    )
    tts_service = NonBlockingTTSService(voice_model=settings.tts_voice_model)

    # 4. Execute Full Turn
    print("\n[4/4] EXECUTING E2E RAG TURN (STT -> RAG -> LLM Active Gen -> TTS)...")
    pcm_bytes = generate_test_pcm()
    query = "What programs are offered by the School of Architecture?"

    start_time = time.time()
    stt_res = stt_service.transcribe_audio(pcm_bytes, sample_rate=16000)
    transcribed = stt_res.text.strip() or query

    # Explicitly force offline mode for local model loading test if desired
    rag_res = chat_service.respond(transcribed, session_id="full_stack_bench")
    reply_text = getattr(rag_res, "reply", getattr(rag_res, "text", str(rag_res)))

    tts_service.speak(reply_text, language="en")
    tts_service.wait_until_done(timeout=15.0)
    elapsed = time.time() - start_time

    stop_monitoring = True
    monitor_thread.join()

    # Calculate actual net values
    net_python_rss = peak_python_rss - python_start_rss
    net_ollama_rss = peak_ollama_rss - ollama_start_rss
    total_combined_peak = peak_combined_rss

    pi_8gb_total_mb = 8192.0
    pi_est_total_mb = 800.0 + peak_python_rss + peak_ollama_rss
    headroom_mb = pi_8gb_total_mb - pi_est_total_mb
    headroom_gb = headroom_mb / 1024.0

    print("\n" + "=" * 76)
    print("        TRUE COMBINED MULTI-PROCESS MEMORY FOOTPRINT BREAKDOWN")
    print("=" * 76)
    print(f"Main Python App Process Baseline RSS   : {python_start_rss:.1f} MB")
    print(f"Main Python App Process Peak RSS       : {peak_python_rss:.1f} MB (+{net_python_rss:.1f} MB net)")
    print(f"Ollama Daemon Peak RSS (Model Loaded) : {peak_ollama_rss:.1f} MB (+{net_ollama_rss:.1f} MB net)")
    print("-" * 76)
    print(f"TRUE COMBINED STACK PEAK RSS MEMORY   : {total_combined_peak:.1f} MB ({total_combined_peak/1024:.2f} GB)")
    print(f"E2E Turn Execution Time               : {elapsed:.2f} seconds")
    print("=" * 76)

    print("\n----------------------------------------------------------------------")
    print("              DEFINITIVE 8GB RASPBERRY PI 5 ASSESSMENT")
    print("----------------------------------------------------------------------")
    print(f"Total Physical RAM on Pi 5           : 8,192.0 MB (8.00 GB)")
    print(f"Python App Process Peak RSS          : {peak_python_rss:.1f} MB")
    print(f"Ollama Daemon Process Peak RSS       : {peak_ollama_rss:.1f} MB")
    print(f"Estimated Total Used on Pi (OS+Stack): {pi_est_total_mb:.1f} MB ({pi_est_total_mb/1024:.2f} GB)")
    print(f"Remaining Free Memory Headroom        : {headroom_mb:.1f} MB ({headroom_gb:.2f} GB)")

    if headroom_gb >= 2.0:
        status = "[OK] FITS WITH COMFORTABLE HEADROOM"
        advice = "The combined stack + Ollama model fits comfortably inside 8GB RAM."
    elif headroom_gb >= 0.5:
        status = "[WARNING] FITS TIGHTLY"
        advice = "The combined stack fits within 8GB RAM, but memory is tight."
    else:
        status = "[ERROR] EXCEEDS 8GB RAM / OOM RISK"
        advice = "The combined stack exceeds safe memory limits."

    print(f"Assessment Result                    : {status}")
    print(f"Recommendation                       : {advice}")
    print("=" * 76 + "\n")

if __name__ == "__main__":
    main()



