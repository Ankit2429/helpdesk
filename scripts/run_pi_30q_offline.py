"""Raspberry Pi 30-Question Offline Benchmark Script.

Executes all 30 benchmark questions in OFFLINE mode on qwen2.5:3b,
logging exact per-question latency and total execution time on Raspberry Pi.
"""

import json
import sys
import time
from pathlib import Path

# Add src and scratch to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scratch"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from audit_full_kb import TEST_QUESTIONS


def main() -> None:
    print("\n" + "=" * 76)
    print("      RASPBERRY PI 30-QUESTION OFFLINE LATENCY BENCHMARK")
    print("      Model: qwen2.5:3b (via Ollama)")
    print("      Connectivity Check: FORCED UNREACHABLE")
    print("=" * 76 + "\n")

    get_settings.cache_clear()
    settings = get_settings()

    settings.enable_cloud_llm_router = True
    settings.connectivity_check_url = "https://invalid-unreachable-host-999.org"

    print("Loading FAISS Index & RAG Pipeline on Pi...")
    rag_pipeline = create_rag_pipeline(settings)
    rag_pipeline.load_index()

    llm_service = create_llm_service(settings)
    context_composer = ContextComposer(settings)

    service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        context_composer=context_composer,
    )

    results = []
    total_latency = 0.0

    print(f"\nRunning 30 questions on Raspberry Pi...\n" + "-" * 76)

    for idx, item in enumerate(TEST_QUESTIONS, 1):
        qid = item["id"]
        cat = item["category"]
        qtext = item["question"]

        print(f"[{idx}/30] Question [{qid}] ({cat})")
        print(f"Query: \"{qtext}\"")

        start_time = time.perf_counter()
        try:
            res = service.respond(qtext, session_id=f"pi_audit_{qid}")
            elapsed = time.perf_counter() - start_time
            total_latency += elapsed

            reply = getattr(res, "reply", getattr(res, "text", str(res))).strip()
            backend = getattr(res, "backend_used", getattr(llm_service, "last_used_backend", "LOCAL"))
            
            print(f"  ► Latency : {elapsed:.2f}s | Backend: {backend}")
            print(f"  ► Answer  : {reply[:120]}...")

            results.append({
                "id": qid,
                "category": cat,
                "question": qtext,
                "latency_seconds": round(elapsed, 2),
                "backend": backend,
                "answer": reply,
            })
        except Exception as err:
            elapsed = time.perf_counter() - start_time
            total_latency += elapsed
            print(f"  ❌ ERROR ({elapsed:.2f}s): {err}")
            results.append({
                "id": qid,
                "category": cat,
                "question": qtext,
                "latency_seconds": round(elapsed, 2),
                "backend": "FAILED",
                "answer": f"ERROR: {err}",
            })

        print("-" * 76)

    avg_latency = total_latency / len(TEST_QUESTIONS)
    out_file = Path(__file__).parent.parent / "scratch" / "pi_30q_offline_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 76)
    print("               RASPBERRY PI BENCHMARK SUMMARY")
    print("=" * 76)
    print(f"Total Benchmark Time : {total_latency:.2f} seconds ({total_latency/60.0:.2f} minutes)")
    print(f"Average Latency / Q  : {avg_latency:.2f} seconds")
    print(f"Results File Saved   : {out_file}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
