from campus_helpdesk.services.intent_router import IntentRouter
from campus_helpdesk.services.language_detector import LanguageDetector

router = IntentRouter()

test_queries = [
    "hi",
    "hello",
    "hey",
    "good morning",
    "thanks",
    "bye",
    "who are you"
]

for q in test_queries:
    det = LanguageDetector.detect(q)
    res = router.route(q, lang_code=det.language)
    print(f"Query: '{q}' -> Intent: {res.intent.value} | Response: {res.response}")
