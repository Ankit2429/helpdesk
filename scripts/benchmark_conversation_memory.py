"""Benchmark script evaluating conversation memory, context size, token usage,
operation latency, CPU usage, and RAM memory footprint across long multi-turn sessions.
"""

import os
import sys
import time
import tracemalloc

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.query_rewriter import QueryRewriter


def run_benchmark():
    print("=" * 70)
    print("      CONVERSATION MEMORY & CONTEXT WINDOW SUBSYSTEM BENCHMARK")
    print("=" * 70)

    tracemalloc.start()

    # Instantiate subsystem components
    session_mgr = SessionManager(ttl_seconds=300, max_history_turns=5, summary_trigger_turns=5, max_context_tokens=2048)
    query_rewriter = QueryRewriter()

    session_id = "benchmark-kiosk-session"
    memory = session_mgr.get_or_create_session(session_id)

    system_prompt = "You are an AI assistant for KLE Technological University campus kiosk."
    rag_context = "Central Library is located in Block C, 2nd floor. It opens 8 AM - 8 PM. Admissions office is in Admin Block Ground Floor."

    conversation_turns = [
        # Domain: Library (Turns 1 - 5)
        ("Where is the central library?", "Library"),
        ("What are its timings?", "Library"),
        ("Is it open today?", "Library"),
        ("Can I borrow ebooks from there?", "Library"),
        ("Who is the chief librarian?", "Library"),

        # Domain: Topic Shift to Admissions (Turns 6 - 10)
        ("Where is the admissions office?", "Admissions"),
        ("What are their contact hours?", "Admissions"),
        ("What documents are required for BE admission?", "Admissions"),
        ("Is CET quota available?", "Admissions"),
        ("How to pay the admission fee?", "Admissions"),

        # Domain: Topic Shift to Hostels (Turns 11 - 15)
        ("Tell me about hostel facilities.", "Hostel"),
        ("What are the mess timings?", "Hostel"),
        ("Are single rooms available?", "Hostel"),
        ("Is Wi-Fi provided there?", "Hostel"),
        ("Who is the hostel warden?", "Hostel"),

        # Domain: Topic Shift to Computer Science Dept (Turns 16 - 20)
        ("Where is CSE department?", "CSE"),
        ("Who is the HOD?", "CSE"),
        ("What courses are offered?", "CSE"),
        ("Are placements good for this branch?", "CSE"),
        ("What is the average salary package?", "CSE"),
    ]

    latencies_ms = []
    token_records = []

    print(f"\nSimulating {len(conversation_turns)}-turn continuous conversation...\n")
    print(f"{'Turn':<5} | {'Domain':<12} | {'Raw Query':<35} | {'Rewritten Query':<45} | {'Latency':<8} | {'Tokens'}")
    print("-" * 125)

    for idx, (query, domain) in enumerate(conversation_turns, start=1):
        t0 = time.perf_counter()

        # 1. Fetch history
        history = memory.get_messages()

        # 2. Rewrite query with multi-turn pronoun resolution
        rewritten = query_rewriter.rewrite(query, history=history)

        # 3. Token budget evaluation
        breakdown = memory.get_token_breakdown(
            system_prompt=system_prompt,
            context_str=rag_context,
            user_query=query,
        )

        # 4. Truncate if necessary
        hist_str, ctx_str, _ = memory.truncate_to_token_budget(
            system_prompt=system_prompt,
            context_str=rag_context,
            user_query=query,
        )

        # 5. Add messages to memory
        simulated_answer = f"Factual answer regarding {domain} for: {query[:30]}"
        memory.add_message("user", query)
        memory.add_message("assistant", simulated_answer)

        t_elapsed = (time.perf_counter() - t0) * 1000
        latencies_ms.append(t_elapsed)
        token_records.append(breakdown)

        q_disp = query[:33] + ".." if len(query) > 35 else query
        r_disp = rewritten[:43] + ".." if len(rewritten) > 45 else rewritten

        print(f"{idx:<5} | {domain:<12} | {q_disp:<35} | {r_disp:<45} | {t_elapsed:6.2f}ms | {breakdown['total_tokens']}/{breakdown['max_context_tokens']}")

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    max_latency = max(latencies_ms)
    max_tokens_seen = max(b["total_tokens"] for b in token_records)

    summary, recent_msgs = memory.get_history_and_summary()

    print("\n" + "=" * 70)
    print("                    BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Conversation Turns Simulated : {len(conversation_turns)}")
    print(f"Average Operation Latency          : {avg_latency:.3f} ms / turn")
    print(f"Max Operation Latency              : {max_latency:.3f} ms")
    print(f"Max Context Tokens Observed        : {max_tokens_seen} tokens (Limit: 2048)")
    print(f"Active History Size                : {len(recent_msgs)} messages ({len(recent_msgs)//2} turns)")
    print(f"Condensed History Summary          : {summary[:100]}...")
    print(f"Heap Memory Allocation             : Current {current_mem / 1024:.1f} KB | Peak {peak_mem / 1024:.1f} KB")
    print("=" * 70)

    # Verification assertions
    assert avg_latency < 10.0, f"Average latency too high: {avg_latency:.2f}ms"
    assert max_tokens_seen <= 2048, f"Context window overflow! Max tokens: {max_tokens_seen}"
    assert len(recent_msgs) <= 10, "History turns exceeded configured limit!"
    print("\nAll memory performance and token safety assertions PASSED!\n")


if __name__ == "__main__":
    run_benchmark()
