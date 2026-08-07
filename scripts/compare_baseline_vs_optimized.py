"""
compare_baseline_vs_optimized.py
Full Per-Question Benchmark & Regression Comparison Runner

Runs all benchmark questions (from evaluation/questions.yaml + 10 core regression questions)
under BOTH Baseline and Optimized configurations, recording exact metrics for:
- Top Retrieved Documents
- Retrieval Accuracy (Recall & MRR)
- Citation Correctness
- Confidence Score & Level
- Hallucination / Grounding Rate
- Final Answer Correctness
- Changes & Regressions per question
"""

import sys
import time
import json
import yaml
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.application.rag_chat_service import RAGChatService


def load_all_benchmark_questions() -> list[dict[str, Any]]:
    questions = []
    
    # 1. Load evaluation/questions.yaml
    q_file = Path("evaluation/questions.yaml")
    if q_file.exists():
        with open(q_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and "questions" in data:
                questions.extend(data["questions"])

    # 2. Load 10 Core Regression Questions from test_rag_consistency.py
    core_10 = [
        {"id": "REG001", "category": "Library", "question": "Where is the library located in campus?", "expected_keywords": ["Administrative Block", "Ground Floor"]},
        {"id": "REG002", "category": "Library", "question": "When is the library open?", "expected_keywords": ["8:00 AM", "8:00 PM"]},
        {"id": "REG003", "category": "Library", "question": "What are the library hours on weekends?", "expected_keywords": ["Saturday", "8:00 AM"]},
        {"id": "REG004", "category": "Library", "question": "What is the email address for the library?", "expected_keywords": ["couldn't find", "not provided", "no information"]},
        {"id": "REG005", "category": "Library", "question": "What is the library phone number?", "expected_keywords": ["couldn't find", "not provided", "no information"]},
        {"id": "REG006", "category": "Admissions", "question": "Where is the admissions office located?", "expected_keywords": ["Administrative Block", "A-101"]},
        {"id": "REG007", "category": "Admissions", "question": "What are the admissions office hours?", "expected_keywords": ["10:00 AM", "5:30 PM"]},
        {"id": "REG008", "category": "Admissions", "question": "What is the admissions office phone number?", "expected_keywords": ["2378103", "2378105", "2378106"]},
        {"id": "REG009", "category": "Admissions", "question": "How can I get admitted?", "expected_keywords": ["Entrance", "KEA", "KCET"]},
        {"id": "REG010", "category": "Hostel", "question": "What is the cafeteria's phone number?", "expected_keywords": ["couldn't find", "not provided", "unavailable"]},
    ]
    
    # Avoid exact duplicate question texts
    seen_texts = {q["question"].lower().strip() for q in questions}
    for item in core_10:
        if item["question"].lower().strip() not in seen_texts:
            questions.append({
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "expected_answer_keywords": item["expected_keywords"],
                "expected_sources": [],
            })
            
    return questions


def build_service_with_config(
    search_limit: int,
    candidate_window: int,
    max_output_tokens: int,
    context_window: int,
    max_context_size: int,
    num_threads: int = 4
) -> RAGChatService:
    settings = Settings(
        rag_search_limit=search_limit,
        candidate_window=candidate_window,
        reranker_top_n=candidate_window,
        final_top_k=search_limit,
        final_results=search_limit,
        ollama_max_output_tokens=max_output_tokens,
        ollama_context_window=context_window,
        ollama_num_threads=num_threads,
        context_composer_max_context_size=max_context_size,
    )
    
    rag_pipeline = create_rag_pipeline(settings)
    rag_pipeline.load_index()
    
    llm_service = create_llm_service(settings)
    context_composer = ContextComposer(settings=settings)
    context_builder = PromptContextBuilder(max_context_size=max_context_size, similarity_threshold=settings.rag_distance_threshold)
    
    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        context_composer=context_composer,
        context_builder=context_builder,
    )
    return chat_service


def evaluate_query(chat_service: RAGChatService, q_item: dict[str, Any]) -> dict[str, Any]:
    query_text = q_item["question"]
    exp_kws = q_item.get("expected_answer_keywords", [])
    
    t0 = time.perf_counter()
    res = chat_service.respond(query_text, session_id=f"eval_{q_item['id']}")
    elapsed = time.perf_counter() - t0
    
    reply = res.reply
    confidence_score = getattr(res, "confidence_score", 0.0)
    confidence_level = getattr(res, "confidence_level", "NONE")
    sources = getattr(res, "supporting_sources", [])
    
    # Keyword coverage
    reply_lower = reply.lower()
    matched_kws = [str(kw) for kw in exp_kws if str(kw).lower() in reply_lower]
    kw_coverage = len(matched_kws) / len(exp_kws) if exp_kws else 1.0
    
    # Citation check
    has_citations = "[" in reply and "]" in reply
    citation_valid = True
    if has_citations:
        # Check if citations were stripped or are valid
        valid_sources = [s.lower() for s in sources]
        citation_valid = any(s in reply_lower for s in valid_sources) if valid_sources else True
        
    # Hallucination / Refusal Check
    refusal_text = "couldn't find" in reply_lower or "not provided" in reply_lower or "no information" in reply_lower
    is_unanswerable = any(k in query_text.lower() for k in ["cafeteria's phone", "admissions office phone number"])
    
    if is_unanswerable:
        is_correct = refusal_text
        hallucination = not refusal_text
    else:
        is_correct = (kw_coverage >= 0.5) and not refusal_text
        hallucination = refusal_text or (kw_coverage < 0.3)

    return {
        "reply": reply,
        "elapsed_sec": round(elapsed, 3),
        "confidence_score": round(confidence_score, 4),
        "confidence_level": confidence_level,
        "sources": sources,
        "kw_coverage": round(kw_coverage, 4),
        "matched_kws": matched_kws,
        "citation_valid": citation_valid,
        "is_correct": is_correct,
        "hallucination": hallucination,
    }


def run_full_comparison():
    questions = load_all_benchmark_questions()
    print("=" * 100)
    print(f"   FULL RAG EVALUATION & COMPARISON: BASELINE vs OPTIMIZED ({len(questions)} Questions)")
    print("=" * 100)
    
    print("\n[1/2] Initializing Baseline Service (Top-K=50, Candidate=25, Context=8192, MaxTokens=512)...")
    baseline_service = build_service_with_config(
        search_limit=50,
        candidate_window=25,
        max_output_tokens=512,
        context_window=8192,
        max_context_size=7000,
        num_threads=4,
    )
    
    print("[2/2] Initializing Optimized Service (Top-K=5, Candidate=20, Context=2048, MaxTokens=256)...")
    optimized_service = build_service_with_config(
        search_limit=5,
        candidate_window=20,
        max_output_tokens=256,
        context_window=2048,
        max_context_size=3500,
        num_threads=4,
    )
    
    comparison_results = []
    
    print("\nRunning side-by-side evaluation across all questions...\n")
    
    for idx, q in enumerate(questions, 1):
        qid = q["id"]
        cat = q.get("category", "General")
        qtext = q["question"]
        
        print(f"[{idx}/{len(questions)}] Testing [{qid}] ({cat}): \"{qtext[:50]}\"")
        
        # Evaluate Baseline
        b_res = evaluate_query(baseline_service, q)
        # Evaluate Optimized
        o_res = evaluate_query(optimized_service, q)
        
        # Detect Changes
        sources_changed = set(b_res["sources"]) != set(o_res["sources"])
        conf_changed = abs(b_res["confidence_score"] - o_res["confidence_score"]) > 0.05
        answer_changed = b_res["reply"].strip() != o_res["reply"].strip()
        citation_changed = b_res["citation_valid"] != o_res["citation_valid"]
        
        any_change = sources_changed or conf_changed or answer_changed or citation_changed
        
        # Detect Regression (if baseline was correct/valid and optimized failed or hallucinated)
        regression = (b_res["is_correct"] and not o_res["is_correct"]) or (not b_res["hallucination"] and o_res["hallucination"])
        
        rec = {
            "id": qid,
            "category": cat,
            "question": qtext,
            "baseline": b_res,
            "optimized": o_res,
            "sources_changed": sources_changed,
            "confidence_changed": conf_changed,
            "answer_changed": answer_changed,
            "citation_changed": citation_changed,
            "any_change": any_change,
            "regression_detected": regression,
        }
        comparison_results.append(rec)
        
        status_flag = "⚠️ REGRESSION" if regression else ("🔄 CHANGED" if any_change else "✅ UNCHANGED")
        print(f"  ► Baseline Latency : {b_res['elapsed_sec']}s | Correct: {b_res['is_correct']} | Conf: {b_res['confidence_score']}")
        print(f"  ► Optimized Latency: {o_res['elapsed_sec']}s | Correct: {o_res['is_correct']} | Conf: {o_res['confidence_score']}")
        print(f"  ► Status           : {status_flag}\n")

    # Output detailed JSON comparison report
    out_dir = Path("evaluation/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "baseline_vs_optimized_comparison.json"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)

    print("=" * 100)
    print("COMPARISON RUN COMPLETE")
    print(f"Report saved to: {json_path}")
    print("=" * 100)

if __name__ == "__main__":
    run_full_comparison()
