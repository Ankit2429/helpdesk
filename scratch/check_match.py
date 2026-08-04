import re
from campus_helpdesk.services.intent_router import IntentRouter

router = IntentRouter()

queries = ["hi", "hello", "hey", "good morning", "thanks", "bye", "who are you"]

for q in queries:
    match = router.CAMPUS_DOMAIN_PATTERN.search(q)
    print(f"Query: '{q}' -> Match: {match}")
