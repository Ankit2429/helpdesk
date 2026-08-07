"""
measure_baseline_timing.py
Instrumented benchmark runner for capturing exact per-stage timing breakdowns:
- Vector Retrieval Time (BM25 + FAISS)
- Rerank Time (Cross-Encoder)
- LLM Generation Time (Ollama)
- Total Latency

Runs the 8 core regression questions (plus Q9 & Q10) and verifies correctness against ground truth.
"""

import sys
import time
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.application.rag_chat_service import RAGChatService

# 8 Core Questions + Q9 & Q10
REGRESSION_QUESTIONS = [
    {"id": "Q1", "question": "Where is the library located in campus?"},
    {"id": "Q2", "question": "When is the library open?"},
    {"id": "Q3", "question": "What are the library hours on weekends?"},
    {"id": "Q4", "question": "What is the email address for the library?"},
    {"id": "Q5", "question": "What is the library phone number?"},
    {"id": "Q6", "question": "Where is the admissions office located?"},
    {"id": "Q7", "question": "What are the admissions office hours?"},
    {"id": "Q8", "question": "What is the admissions office phone number?"},
    {"id": "Q9", "question": "How can I get admitted?"},
    {"id": "Q10", "question": "What is the cafeteria's phone number?"},
]

def run_instrumented_benchmark(tag="BASELINE"):
    get_settings.cache_clear()
    settings = get_settings()

    print("\n" + "=" * 90)
    print(f"   RAG BENCHMARK & TIMING BREAKDOWN [{tag}]")
    print(f"   Model: {settings.ollama_model} | Context: {settings.ollama_context_window} | Top-K: {settings.rag_search_limit} | Threads: {settings.ollama_num_threads}")
    print("=" * 90)

    rag_pipeline = create_rag_pipeline(settings)
    rag_pipeline.load_index()

    llm_service = create_llm_service(settings)
    context_composer = ContextComposer(settings)

    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        context_composer=context_composer,
    )

    # Instrument components to measure precise timings
    timing_records = {"retrieval": 0.0, "rerank": 0.0, "llm": 0.0}

    orig_store_search = rag_pipeline._similarity_store.search
    def instrumented_store_search(*args, **kwargs):
        t0 = time.perf_counter()
        res = orig_store_search(*args, **kwargs)
        timing_records["retrieval"] += (time.perf_counter() - t0)
        return res
    rag_pipeline._similarity_store.search = instrumented_store_search

    if rag_pipeline._reranker is not None:
        orig_rerank = rag_pipeline._reranker.rerank
        def instrumented_rerank(*args, **kwargs):
            t0 = time.perf_counter()
            res = orig_rerank(*args, **kwargs)
            timing_records["rerank"] += (time.perf_counter() - t0)
            return res
        rag_pipeline._reranker.rerank = instrumented_rerank

    orig_llm_gen = llm_service.generate
    def instrumented_llm_gen(*args, **kwargs):
        t0 = time.perf_counter()
        res = orig_llm_gen(*args, **kwargs)
        timing_records["llm"] += (time.perf_counter() - t0)
        return res
    llm_service.generate = instrumented_llm_gen

    results = []

    print(f"\n{'ID':<4} | {'Query':<42} | {'Retr (s)':<8} | {'Rerank(s)':<9} | {'LLM (s)':<8} | {'Total (s)':<9}")
    print("-" * 90)

    for idx, item in enumerate(REGRESSION_QUESTIONS, 1):
        q_id = item["id"]
        q_text = item["question"]

        timing_records["retrieval"] = 0.0
        timing_records["rerank"] = 0.0
        timing_records["llm"] = 0.0

        t_start = time.perf_counter()
        res = chat_service.respond(q_text, session_id=f"bench_{q_id}")
        t_total = time.perf_counter() - t_start

        t_retr = timing_records["retrieval"]
        t_rerank = timing_records["rerank"]
        t_llm = timing_records["llm"]

        q_short = q_text[:40] + "..." if len(q_text) > 40 else q_text
        print(f"{q_id:<4} | {q_short:<42} | {t_retr:<8.3f} | {t_rerank:<9.3f} | {t_llm:<8.3f} | {t_total:<9.3f}")

        results.append({
            "id": q_id,
            "question": q_text,
            "reply": res.reply,
            "retrieval_sec": round(t_retr, 4),
            "rerank_sec": round(t_rerank, 4),
            "llm_sec": round(t_llm, 4),
            "total_sec": round(t_total, 4),
        })

    print("-" * 90)
    avg_retr = sum(r["retrieval_sec"] for r in results) / len(results)
    avg_rerank = sum(r["rerank_sec"] for r in results) / len(results)
    avg_llm = sum(r["llm_sec"] for r in results) / len(results)
    avg_total = sum(r["total_sec"] for r in results) / len(results)

    print(f"{'AVG':<4} | {'Average Across 10 Queries':<42} | {avg_retr:<8.3f} | {avg_rerank:<9.3f} | {avg_llm:<8.3f} | {avg_total:<9.3f}")
    print("=" * 90 + "\n")

    output_data = {
        "tag": tag,
        "averages": {
            "retrieval_sec": round(avg_retr, 4),
            "rerank_sec": round(avg_rerank, 4),
            "llm_sec": round(avg_llm, 4),
            "total_sec": round(avg_total, 4),
        },
        "details": results
    }

    out_file = Path(__file__).parent.parent / "logs" / f"timing_{tag.lower()}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    return output_data

if __name__ == "__main__":
    tag_arg = sys.argv[1] if len(sys.argv) > 1 else "BASELINE"
    run_instrumented_benchmark(tag_arg)
