"""
ttt_service.py
Text-to-Text understanding and reply generation service.

Production Pi Architecture Strategy for Multilingual Safety:
- English ('en'): Fast pre-checks -> FAISS + Ollama (qwen2.5:1.5b) RAG pipeline.
- Kannada ('kn') & Hindi ('hi'): Strict Canned-Only Mode.
  Matches queries against human-verified canned FAQ responses (greetings, library location/hours/contact,
  admissions location/hours/process). Every canned entry strictly requires matching both the Entity
  AND the specific Intent Attribute being asked about. If an attribute is missing or unmatched (e.g.
  Admissions Phone), it routes directly to the honest English fallback phrase.
"""

import datetime
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ttt_service")


def round_time_to_5_min(dt: datetime.datetime | None = None) -> str:
    if dt is None:
        dt = datetime.datetime.now()
    minute = 5 * round(dt.minute / 5.0)
    if minute == 60:
        dt += datetime.timedelta(hours=1)
        minute = 0
    rounded_dt = dt.replace(minute=minute, second=0, microsecond=0)
    time_str = rounded_dt.strftime("%I:%M %p")
    if time_str.startswith("0"):
        time_str = time_str[1:]
    return time_str


# Human-verified Indic canned FAQ responses
CANNED_FAQ = {
    "kn": {
        "greeting": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        "library_location": "ಗ್ರಂಥಾಲಯವು ಬ್ಲಾಕ್ ಸಿ, ೨ನೇ ಮಹಡಿಯಲ್ಲಿದೆ.",
        "library_hours": "ಗ್ರಂಥಾಲಯವು ಸೋಮವಾರದಿಂದ ಶನಿವಾರದವರೆಗೆ ಬೆಳಿಗ್ಗೆ ೮:೦೦ ರಿಂದ ರಾತ್ರಿ ೮:೦೦ ರವರೆಗೆ ತೆರೆದಿರುತ್ತದೆ. ಭಾನುವಾರ ಮುಚ್ಚಿರುತ್ತದೆ.",
        "library_email": "ಗ್ರಂಥಾಲಯದ ಇಮೇಲ್ ವಿಳಾಸ: library@campus.edu.",
        "library_phone": "ಗ್ರಂಥಾಲಯದ ಫೋನ್ ಸಂಖ್ಯೆ: 555-0199.",
        "admissions_location": "ಅಡ್ಮಿಷನ್ ಕಚೇರಿಯು ಬ್ಲಾಕ್ ಎ, ನೆಲಮಹಡಿಯಲ್ಲಿದೆ.",
        "admissions_hours": "ಅಡ್ಮಿಷನ್ ಕಚೇರಿಯು ವಾರದ ದಿನಗಳಲ್ಲಿ ಬೆಳಿಗ್ಗೆ ೧೦:೦೦ ರಿಂದ ಸಂಜೆ ೪:೦೦ ರವರೆಗೆ ತೆರೆದಿರುತ್ತದೆ.",
        "admissions_process": "ಅಧಿಕೃತ ಆನ್‌ಲೈನ್ ಪೋರ್ಟಲ್ ಮೂಲಕ ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಸಲ್ಲಿಸಿ.",
        "fallback": "ಸವಿಸ್ತಾರವಾದ ಮಾಹಿತಿಗಾಗಿ ದಯವಿಟ್ಟು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕೇಳಿ.",
    },
    "hi": {
        "greeting": "नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ?",
        "library_location": "पुस्तकालय ब्लॉक सी, दूसरी मंजिल पर स्थित है।",
        "library_hours": "पुस्तकालय सोमवार से शनिवार सुबह 8:00 बजे से रात 8:00 बजे तक खुला रहता है। रविवार को बंद रहता है।",
        "library_email": "पुस्तकालय का ईमेल पता: library@campus.edu.",
        "library_phone": "पुस्तकालय का फोन नंबर: 555-0199.",
        "admissions_location": "प्रवेश कार्यालय ब्लॉक ए, भूतल पर स्थित है।",
        "admissions_hours": "प्रवेश कार्यालय कार्यदिवसों में सुबह 10:00 बजे से शाम 4:00 बजे तक खुला रहता है।",
        "admissions_process": "आधिकारिक ऑनलाइन पोर्टल के माध्यम से अपना आवेदन जमा करें।",
        "fallback": "विस्तृत जानकारी के लिए कृपया अंग्रेजी में पूछें।",
    },
}


def is_current_time_query(text_lower: str) -> bool:
    """Check if query is asking for current clock time (not entity opening/closing hours)."""
    has_time_phrase = bool(re.search(r"(what time|clock|current time|time is it|time right now|ಸಮಯ ಎಷ್ಟು|ಸಮಯ ಏನು|समय क्या|समय कितना)", text_lower))
    has_entity_or_schedule = bool(re.search(
        r"(library|admissi|cafeteria|office|dept|department|open|close|closing|opening|hours|ಗ್ರಂಥಾಲಯ|ಅಡ್ಮಿಷನ್|ಪ್ರವೇಶ|ಪುಸ್ತಕ|ಪುಸ್ತಕಾ|ತೆರೆದ|ತೆರೆದಿ|ಮುಚ್ಚು|ಪುಸ್ತಕಾ|पुस्तकालय|प्रवेश|खुलता|बंद)",
        text_lower
    ))
    return has_time_phrase and not has_entity_or_schedule


class TTTService:
    """
    Hybrid TTT Service matching production Pi architecture:
    - Pre-check fast keyword rules (greeting, time).
    - Indic (HI / KN): Strict Canned-Only FAQ mode (Entity + Attribute matching).
    - English (EN): RAGChatService (FAISS + Ollama LLM).
    """

    def __init__(self):
        self._init_rag()

    def _init_rag(self) -> None:
        """Initialize RAGChatService with FAISS vector store + Ollama LLM for English queries."""
        self.rag_service = None
        try:
            from campus_helpdesk.config.settings import get_settings
            from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
            from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
            from campus_helpdesk.application.rag_chat_service import RAGChatService

            settings = get_settings()
            logger.info(f"Initializing RAGChatService (FAISS + Ollama model='{settings.ollama_model}')...")

            rag_pipeline = create_rag_pipeline(settings)
            llm_service = OllamaLLMService(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
                generation_options=settings.ollama_options,
            )

            self.rag_service = RAGChatService(
                llm_service=llm_service,
                rag_pipeline=rag_pipeline,
                distance_threshold=settings.rag_distance_threshold,
            )
            logger.info("RAGChatService (FAISS + Ollama) ready.")
        except Exception as e:
            logger.warning(f"Could not initialize RAGChatService ({e}). Fallback intent matching will be used.")

    def _handle_indic_canned(self, text_lower: str, lang_code: str) -> str:
        """Match query against human-verified Indic FAQ database or return English fallback phrase."""
        faq = CANNED_FAQ.get(lang_code, CANNED_FAQ["kn"])

        # Helper boolean checks for strict Entity + Attribute matching
        is_library = bool(re.search(r"(library|ಗ್ರಂಥಾಲಯ|ಪುಸ್ತಕ|ಪುಸ್ತಕಾ|ग्रंथालय|गंतालय|गंत|ग्रन्त्|ग्रन्त|पुस्तकालय)", text_lower))
        is_admissions = bool(re.search(r"(admissi|ಅಡ್ಮಿಷನ್|ಪ್ರವೇಶ|एडमिशन|प्रवेश)", text_lower))

        is_location = bool(re.search(r"(where|locat|ಎಲ್ಲಿದೆ|ಸ್ಥಳ|ಎಲ್ಲಿ|कहाँ|कहां|स्थान|येल्लिदे|यल्लिदे|दिल्लिदे|ದಿಲ್ಲಿದೆ)", text_lower))
        is_hours = bool(re.search(r"(hour|open|weekend|sunday|ಸಮಯ|ತೆರೆದಿ|ವಾರಾಂತ್ಯ|ಭಾನುವಾರ|समय|कब|खुला)", text_lower))
        is_email = bool(re.search(r"(email|ಇಮೇಲ್|ईमेल)", text_lower))
        is_phone = bool(re.search(r"(phone|number|ಫೋನ್|ಸಂಖ್ಯೆ|फोन|नंबर)", text_lower))
        is_apply = bool(re.search(r"(apply|admitted|how.*get|ಹೇಗೆ|ಅರ್ಜಿ|आवेदन|कैसे)", text_lower))

        # 1. Greetings
        if re.search(r"(hello|hi|hey|greetings|welcome|नमस्ते|ನಮಸ್ಕಾರ)", text_lower):
            return faq["greeting"]

        # 2. Library Email (Entity: Library + Attribute: Email)
        if is_library and is_email:
            return faq["library_email"]

        # 3. Library Phone (Entity: Library + Attribute: Phone)
        if is_library and is_phone:
            return faq["library_phone"]

        # 4. Library Location (Entity: Library + Attribute: Location)
        if is_library and is_location:
            return faq["library_location"]

        # 5. Library Hours (Entity: Library + Attribute: Hours/Days)
        if is_library and is_hours:
            return faq["library_hours"]

        # 6. Admissions Location (Entity: Admissions + Attribute: Location)
        if is_admissions and is_location:
            return faq["admissions_location"]

        # 7. Admissions Hours (Entity: Admissions + Attribute: Hours/Time)
        if is_admissions and is_hours:
            return faq["admissions_hours"]

        # 8. Admissions Process / How to Apply (Entity: Admissions + Attribute: How/Apply)
        if is_admissions and is_apply:
            return faq["admissions_process"]

        # 9. Generic system time query (e.g. "what time is it", "ಸಮಯ ಎಷ್ಟು", "समय कितना हुआ")
        if is_current_time_query(text_lower):
            now_str = round_time_to_5_min()
            if lang_code == "hi":
                return f"अभी समय {now_str} है।"
            return f"ಈಗ ಸಮಯ {now_str} ಆಗಿದೆ।"

        # 10. Fallback phrase for unmatched queries outside canned set (including missing attributes like Admissions Phone)
        logger.info(f"TTT [Indic Canned Mode]: No FAQ match for query '{text_lower}'. Returning English-fallback phrase.")
        return faq["fallback"]

    def get_reply(self, user_text: str, language: str = "en") -> str:
        """
        Process user query:
        - Indic (HI / KN): Strict Canned-Only FAQ lookup (Entity + Attribute matching).
        - English (EN): Fast intent pre-checks -> RAG (FAISS + Ollama).
        """
        if not user_text or not user_text.strip():
            return "I didn't hear anything."

        text_lower = user_text.lower().strip()
        lang_code = language.lower()[:2]

        # Indic languages: Strict Canned FAQ mode only (0% hallucination)
        if lang_code in ("hi", "kn"):
            reply = self._handle_indic_canned(text_lower, lang_code)
            logger.info(f"TTT [Indic Strict Canned Mode ({lang_code.upper()})]: \"{reply}\"")
            return reply

        # English: Fast intent pre-check
        if re.search(r"(hello|hi|hey|greetings|welcome)", text_lower):
            return "Hello! Welcome to our campus. How can I assist you today?"
        if is_current_time_query(text_lower):
            return f"It is currently {round_time_to_5_min()}."

        # English: Open-ended RAG pipeline
        if self.rag_service is not None:
            try:
                logger.info(f"TTT [RAG Pipeline Ollama (EN)]: Querying FAISS + Ollama for \"{user_text}\"...")
                chat_result = self.rag_service.respond(user_text)
                answer = chat_result.reply if hasattr(chat_result, "reply") else str(chat_result)
                logger.info(f"TTT [RAG Answer Generated]: \"{answer}\"")
                return answer
            except Exception as exc:
                logger.warning(f"RAG query error ({exc}). Falling back to help desk summary.")

        return (
            "I am your Campus Helpdesk Robot! I can help you with campus directions, "
            "library hours, department locations, and general student guidance."
        )


# ---- Quick manual test -------------------------------------------------------
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    service = TTTService()

    tests = [
        ("hello", "en"),
        ("Where is the computer science department located?", "en"),
        ("ಗ್ರಂಥಾಲಯವು ಕ್ಯಾಂಪಸ್‌ನಲ್ಲಿ ಎಲ್ಲಿದೆ?", "kn"),
        ("ಅಡ್ಮಿಷನ್ ಕಚೇರಿ ಎಲ್ಲಿದೆ?", "kn"),
        ("ಅಡ್ಮಿಷನ್ ಕಚೇರಿಯ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?", "kn"),
        ("ಕೆಫೆಟೇರಿಯಾದ ಫೋನ್ ಸಂಖ್ಯೆ ಏನು?", "kn"),
    ]

    for q, lang in tests:
        print(f"\nUser ({lang.upper()}): {q}")
        reply = service.get_reply(q, language=lang)
        print(f"Robot ({lang.upper()}): {reply}")
