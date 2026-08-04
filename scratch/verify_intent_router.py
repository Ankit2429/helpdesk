"""Verify the live intent_router patterns work correctly for all test cases."""
import sys
sys.path.insert(0, "src")

from campus_helpdesk.services.intent_router import IntentRouter, IntentType

router = IntentRouter()

tests = [
    # (query, expected_intent_type)
    ("hii", IntentType.GREETING),
    ("hi", IntentType.GREETING),
    ("hello", IntentType.GREETING),
    ("heyy", IntentType.GREETING),
    ("hey", IntentType.GREETING),
    ("hiiii", IntentType.GREETING),
    ("HELLO", IntentType.GREETING),
    ("depatments", IntentType.CAMPUS_QUERY),
    ("departments", IntentType.CAMPUS_QUERY),
    ("dept", IntentType.CAMPUS_QUERY),
    ("hostel", IntentType.CAMPUS_QUERY),
    ("library", IntentType.CAMPUS_QUERY),
    ("cse", IntentType.CAMPUS_QUERY),
    ("what are the departments", IntentType.CAMPUS_QUERY),
    ("show me depatments list", IntentType.CAMPUS_QUERY),
    ("thanks", IntentType.THANKS),
    ("bye", IntentType.GOODBYE),
    ("who are you", IntentType.IDENTITY),
]

print("Live IntentRouter Verification:")
print("-" * 60)
all_pass = True
for query, expected in tests:
    result = router.route(query, lang_code="en")
    status = "PASS" if result.intent == expected else "FAIL"
    print(f'{status}: "{query}" -> {result.intent.value} (expected {expected.value})')
    if result.intent != expected:
        all_pass = False

print()
print("All passed!" if all_pass else "SOME TESTS FAILED!")
