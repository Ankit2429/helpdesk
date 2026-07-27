"""
test_rag_consistency.py
Comprehensive 10-question strict factual accuracy suite across library and admissions knowledge.
Includes Q9 (Rephrased Answerable Query) and Q10 (Genuinely Unanswerable Query).
"""

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ttt_service import TTTService


def verify_location(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    passed = "block c" in text and "2nd" in text
    reason = "Contains 'Block C' and '2nd floor'" if passed else f"Inaccurate response: '{reply}'"
    return passed, reason


def verify_hours(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    if "10:00" in text or "6:00" in text:
        return False, f"CONTRADICTION: Contains hallucinated hours ('10:00 AM' / '6:00 PM'): '{reply}'"
    if "sunday" in text and "open" in text and "closed" not in text:
        return False, f"CONTRADICTION: Claims library is open on Sunday: '{reply}'"
    if "8:00 am" not in text or "8:00 pm" not in text:
        return False, f"INACCURATE: Missing ground-truth hours '8:00 AM to 8:00 PM': '{reply}'"
    return True, "Strictly factually accurate"


def verify_weekend_hours(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    if "10:00" in text or "6:00" in text:
        return False, f"CONTRADICTION: Contains hallucinated hours: '{reply}'"
    if "closed" not in text:
        return False, f"INACCURATE: Fails to state library is Closed on Sundays: '{reply}'"
    return True, "Strictly factually accurate"


def verify_email(reply: str) -> tuple[bool, str]:
    passed = "library@campus.edu" in reply.lower()
    reason = "Contains 'library@campus.edu'" if passed else f"Inaccurate email: '{reply}'"
    return passed, reason


def verify_phone(reply: str) -> tuple[bool, str]:
    passed = "555-0199" in reply.lower()
    reason = "Contains '555-0199'" if passed else f"Inaccurate phone number: '{reply}'"
    return passed, reason


def verify_admissions_location(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    passed = "block a" in text and "ground" in text
    reason = "Contains 'Block A, ground floor'" if passed else f"Inaccurate admissions location: '{reply}'"
    return passed, reason


def verify_admissions_hours(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    passed = "10:00 am" in text and "4:00 pm" in text
    reason = "Contains '10:00 AM to 4:00 PM'" if passed else f"Inaccurate admissions hours: '{reply}'"
    return passed, reason


def verify_admissions_phone(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    refusal_keywords = [
        "not", "don't", "doesn't", "unavailable", "no information", 
        "cannot", "not provided", "not mentioned", "not listed", "unknown", "no phone"
    ]
    if any(kw in text for kw in refusal_keywords):
        return True, "Factually grounded: Correctly stated phone number is not available"

    return False, f"HALLUCINATION: Model fabricated a non-existent phone number: '{reply}'"


def verify_how_to_apply(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    apply_keywords = ["online portal", "application", "portal", "apply", "official"]
    if any(kw in text for kw in apply_keywords):
        return True, "Correctly answered rephrased query from admissions application process"
    return False, f"FAILED: Over-cautious refusal or missed application instructions: '{reply}'"


def verify_cafeteria_phone(reply: str) -> tuple[bool, str]:
    text = reply.lower()
    refusal_keywords = [
        "not", "don't", "doesn't", "unavailable", "no information", 
        "cannot", "not provided", "not mentioned", "not listed", "unknown", "no phone"
    ]
    if any(kw in text for kw in refusal_keywords):
        return True, "Factually grounded: Correctly refused unanswerable cafeteria phone query"
    return False, f"HALLUCINATION: Fabricated information for unanswerable query: '{reply}'"


TEST_SUITE = [
    {
        "id": "Q1",
        "question": "Where is the library located in campus?",
        "verifier": verify_location,
        "description": "Library Location Query",
    },
    {
        "id": "Q2",
        "question": "When is the library open?",
        "verifier": verify_hours,
        "description": "Library Operating Hours (Phrasing A)",
    },
    {
        "id": "Q3",
        "question": "What are the library hours on weekends?",
        "verifier": verify_weekend_hours,
        "description": "Library Weekend Hours (Phrasing B)",
    },
    {
        "id": "Q4",
        "question": "What is the email address for the library?",
        "verifier": verify_email,
        "description": "Library Contact Email Query",
    },
    {
        "id": "Q5",
        "question": "What is the library phone number?",
        "verifier": verify_phone,
        "description": "Library Phone Number Query",
    },
    {
        "id": "Q6",
        "question": "Where is the admissions office located?",
        "verifier": verify_admissions_location,
        "description": "Admissions Location Query",
    },
    {
        "id": "Q7",
        "question": "What are the admissions office hours?",
        "verifier": verify_admissions_hours,
        "description": "Admissions Operating Hours Query",
    },
    {
        "id": "Q8",
        "question": "What is the admissions office phone number?",
        "verifier": verify_admissions_phone,
        "description": "Admissions Non-Existent Phone Number (Refusal Test)",
    },
    {
        "id": "Q9",
        "question": "How can I get admitted?",
        "verifier": verify_how_to_apply,
        "description": "Rephrased Answerable Query (How to Apply)",
    },
    {
        "id": "Q10",
        "question": "What is the cafeteria's phone number?",
        "verifier": verify_cafeteria_phone,
        "description": "Genuinely Unanswerable Query (Cafeteria Phone Refusal)",
    },
]


def main():
    print("\n=======================================================================")
    print("   STRICT FACTUAL ACCURACY 10-QUESTION TEST SUITE (qwen2.5:1.5b)")
    print("=======================================================================")

    service = TTTService()
    results = []

    for test in TEST_SUITE:
        q_id = test["id"]
        q_text = test["question"]
        verifier = test["verifier"]
        desc = test["description"]

        print(f">>> [{q_id}] Testing: \"{q_text}\" ({desc})")
        t0 = time.time()
        reply = service.get_reply(q_text, language="en")
        elapsed = time.time() - t0

        passed, reason = verifier(reply)
        results.append({
            "id": q_id,
            "question": q_text,
            "reply": reply,
            "elapsed": elapsed,
            "reason": reason,
            "passed": passed,
        })

        print(f"    Answer   : \"{reply}\"")
        print(f"    Latency  : {elapsed:.2f} s")
        print(f"    Status   : {'PASSED ✓' if passed else 'FAILED ✗'} ({reason})\n")

    print("=" * 80)
    print("SUMMARY RESULTS TABLE:")
    print("=" * 80)
    print(f"{'ID':<4} | {'Query Phrasing':<45} | {'Latency':<8} | {'Status':<10}")
    print("-" * 80)
    pass_count = 0
    fail_count = 0
    for r in results:
        status_str = "PASSED ✓" if r["passed"] else "FAILED ✗"
        if r["passed"]:
            pass_count += 1
        else:
            fail_count += 1
        print(f"{r['id']:<4} | {r['question']:<45} | {r['elapsed']:.2f}s   | {status_str:<10}")

    print("=" * 80)
    print(f"FINAL SCORE: {pass_count} PASSED / {fail_count} FAILED out of {len(TEST_SUITE)} tests.")
    print("=" * 80)


if __name__ == "__main__":
    main()
