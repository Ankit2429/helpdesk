#!/usr/bin/env python
"""
intent_router_verification.py — Phase 3 Verification Suite for Intent Router & RAG Pipeline

Tests:
  1. Hi
  2. Hello
  3. Good Morning
  4. Thank You
  5. Bye
  6. Who are you?
  7. What can you do?
  8. Principal
  9. Hostel
 10. Admissions
 11. ISE Department

Verifies:
  - Greetings & conversational intents bypass RAG
  - Campus questions use RAG
  - Streaming interface works
  - PASS / FAIL report for every query
"""

import sys
import json
import logging

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.touch_app import build_chat_service
from campus_helpdesk.services.intent_router import IntentRouter, IntentType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("intent_verification")

VERIFY_QUERIES = [
    {"query": "Hi", "expected_bypass_rag": True},
    {"query": "Hello", "expected_bypass_rag": True},
    {"query": "Good Morning", "expected_bypass_rag": True},
    {"query": "Thank You", "expected_bypass_rag": True},
    {"query": "Bye", "expected_bypass_rag": True},
    {"query": "Who are you?", "expected_bypass_rag": True},
    {"query": "What can you do?", "expected_bypass_rag": True},
    {"query": "Principal", "expected_bypass_rag": False},
    {"query": "Hostel", "expected_bypass_rag": False},
    {"query": "Admissions", "expected_bypass_rag": False},
    {"query": "ISE Department", "expected_bypass_rag": False},
]

def run_verification():
    print("=" * 80)
    print("PHASE 3 — INTENT ROUTER & CONVERSATIONAL AI VERIFICATION SUITE")
    print("=" * 80)

    chat_service = build_chat_service()
    router = IntentRouter()

    results = []

    for idx, item in enumerate(VERIFY_QUERIES, 1):
        q = item["query"]
        exp_bypass = item["expected_bypass_rag"]

        print("\n" + "=" * 80)
        print(f"QUERY [{idx}/11]: '{q}'")
        print("=" * 80)

        # 1. Intent Classification Check
        intent_res = router.route(q, lang_code="en")
        actual_bypass = (intent_res.intent != IntentType.CAMPUS_QUERY)

        print(f"Intent Classified: {intent_res.intent.value.upper()}")
        print(f"Bypass RAG Target: Expected={exp_bypass} | Actual={actual_bypass}")

        # 2. Test respond() method
        session_id = f"verify-intent-{idx}"
        res = chat_service.respond(q, session_id=session_id)
        reply = res.reply.strip()

        print("\nResponse:")
        print("-" * 60)
        print(reply)
        print("-" * 60)

        # 3. Test respond_stream() streaming interface
        stream_tokens = list(chat_service.respond_stream(q, session_id=f"stream-{idx}"))
        stream_full = "".join(stream_tokens).strip()

        fallback_refusal = "I couldn't find that information in my knowledge base."
        passed = (reply != fallback_refusal and len(reply) > 10 and actual_bypass == exp_bypass and bool(stream_full))

        status = "PASS" if passed else "FAIL"
        print(f"\nVERIFICATION RESULT: {status}")

        results.append({
            "id": idx,
            "query": q,
            "intent": intent_res.intent.value,
            "bypassed_rag": actual_bypass,
            "reply_preview": reply[:120],
            "streaming_ok": bool(stream_full),
            "passed": passed,
            "status": status,
        })

    print("\n" + "=" * 80)
    print("INTENT ROUTER VERIFICATION SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for r in results:
        print(f"[{r['status']}] Query '{r['query']}' -> Intent: {r['intent'].upper()} | Bypassed RAG: {r['bypassed_rag']}")

    print("-" * 80)
    print(f"TOTAL SCORE: {passed_count} / {total_count} ({passed_count/total_count*100:.1f}%)")
    print("=" * 80)

    with open("intent_router_verification_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✓ Saved verification report to intent_router_verification_report.json")
    return results

if __name__ == "__main__":
    run_verification()
