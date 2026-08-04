import re
from campus_helpdesk.services.intent_router import IntentRouter

router = IntentRouter()

prefixes = [
    "Respond only in Kannada script. hi",
    "Respond only in Hindi script. hi",
    "Respond in Hinglish: a natural Hindi-English mix, written in Latin script. hi",
    "Respond in Kanglish: a natural Kannada-English mix, written in Latin script. hi",
    "Respond in English. hi",
    "Respond in english. hi",
    "Respond in English. hello",
]

for text in prefixes:
    has_campus = bool(router.CAMPUS_DOMAIN_PATTERN.search(text))
    res = router.route(text, lang_code="en")
    print(f"Text: {text} -> Has Campus: {has_campus} | Intent: {res.intent.value} | Response: {res.response is not None}")
