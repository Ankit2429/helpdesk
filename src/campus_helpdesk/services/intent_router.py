"""Lightweight Intent Router for Conversational AI & Campus Helpdesk.

Classifies incoming user messages into intent types:
  - GREETING
  - GOODBYE
  - THANKS
  - IDENTITY
  - CAPABILITIES
  - SMALL_TALK
  - CAMPUS_QUERY

Non-campus conversational intents bypass RAG vector search and return fast, predefined
multilingual responses in English, Kannada, Hindi, Hinglish, or Kanglish.
"""

import enum
import re
from typing import NamedTuple


class IntentType(enum.Enum):
    GREETING = "greeting"
    GOODBYE = "goodbye"
    THANKS = "thanks"
    IDENTITY = "identity"
    CAPABILITIES = "capabilities"
    SMALL_TALK = "small_talk"
    CAMPUS_QUERY = "campus_query"


class IntentResult(NamedTuple):
    intent: IntentType
    response: str | None = None
    confidence: float = 1.0


class IntentRouter:
    """Classifies user intent using pattern matching and provides multilingual responses."""

    # Patterns for intent classification
    GREETING_PATTERN = re.compile(
        # Core greetings + informal repetition variants (hii, hiii, heyyy, etc.)
        r"\b(hi+|he+y+|hello+|greetings|good morning|good afternoon|good evening|namaste|namaskara|namaskar|namskara|hi there|hey there|suprabhata)\b",
        re.IGNORECASE,
    )

    GOODBYE_PATTERN = re.compile(
        r"\b(bye|goodbye|see you|ta ta|cya|take care|bye bye|shubhadina|alvida)\b",
        re.IGNORECASE,
    )

    THANKS_PATTERN = re.compile(
        r"\b(thank you|thanks|thanku|thx|thanks a lot|dhanyavadagalu|dhanyavad|shukriya|dhanyawad)\b",
        re.IGNORECASE,
    )

    IDENTITY_PATTERN = re.compile(
        r"\b(who are you|what is your name|who r u|your name|introduce yourself|tell me about yourself|who created you|who made you|yaaru neenu|ninnu yaaru|aap kaun hain|aap kaun ho)\b",
        re.IGNORECASE,
    )

    CAPABILITIES_PATTERN = re.compile(
        r"\b(what can you do|what are your features|how can you help|what do you do|help me|menu|features|capabilities|what can u do|enu madabahudu|kya kar sakte ho)\b",
        re.IGNORECASE,
    )

    SMALL_TALK_PATTERN = re.compile(
        r"\b(how are you|how r u|how is it going|how r ya|hege idira|hegidira|aap kaise hain|kaise ho|what's up|what s up|tell me a joke|are you human|do you like|are you smart)\b",
        re.IGNORECASE,
    )

    # Campus domain keywords to ensure campus questions are NEVER misclassified as small talk
    # Includes common misspellings: depatments (transposition), deptartment, etc.
    CAMPUS_DOMAIN_PATTERN = re.compile(
        r"\b(principal|vc|vice chancellor|chancellor|dean|hod|director|hostel|mess|canteen|fee|fees|admission|admissions|course|courses|departments?|depatments?|dept|depts|ise|cse|ece|eee|me|mech|ce|civil|bt|biotech|mba|mca|bca|bba|be|btech|mtech|phd|library|placement|placements|exam|timetable|syllabus|results|building|auditorium|kle|kletech|bvb|campus|hubballi|scholarship|cutoff|eligibility|contact|phone|email|address)\b",
        re.IGNORECASE,
    )

    RESPONSE_TEMPLATES: dict[IntentType, dict[str, str]] = {
        IntentType.GREETING: {
            "en": "Hello! Welcome to KLE Technological University (BVB Campus) AI Helpdesk. How can I assist you today?",
            "hi": "नमस्ते! केएलई टेक्नोलॉजिकल यूनिवर्सिटी (बीवीबी परिसर) एआई हेल्पडेस्क में आपका स्वागत है। मैं आज आपकी क्या सहायता कर सकता हूँ?",
            "kn": "ನಮಸ್ಕಾರ! ಕೆಎಲ್‌ಇ ತಾಂತ್ರಿಕ ವಿಶ್ವವಿದ್ಯಾಲಯ (ಬಿವಿಬಿ ಕ್ಯಾಂಪಸ್) AI ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್‌ಗೆ ಸ್ವಾಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        },
        IntentType.GOODBYE: {
            "en": "Goodbye! Have a wonderful day at KLE Tech campus. Feel free to ask if you need anything else!",
            "hi": "अलविदा! केएलई टेक परिसर में आपका दिन शुभ हो। यदि आपको किसी और सहायता की आवश्यकता हो तो अवश्य पूछें!",
            "kn": "ವಂದನೆಗಳು! ಕೆಎಲ್‌ಇ ಟೆಕ್ ಕ್ಯಾಂಪಸ್‌ನಲ್ಲಿ ನಿಮ್ಮ ದಿನ ಶುಭವಾಗಿರಲಿ. ಮತ್ತೆ ಸಹಾಯ ಬೇಕಿದ್ದರೆ ಕೇಳಿ!",
        },
        IntentType.THANKS: {
            "en": "You're very welcome! I'm happy to help you with any information about KLE Technological University.",
            "hi": "आपका बहुत-बहुत स्वागत है! केएलई टेक्नोलॉजिकल यूनिवर्सिटी की जानकारी देकर मुझे खुशी हुई।",
            "kn": "ನಿಮಗೆ ಸುಸ್ವಾಗತ! ಕೆಎಲ್‌ಇ ತಾಂತ್ರಿಕ ವಿಶ್ವವಿದ್ಯಾಲಯದ ವಿವರ ನೀಡಲು ನನಗೆ ಸಂತೋಷವಾಗಿದೆ.",
        },
        IntentType.IDENTITY: {
            "en": "I am Sparky (Campus Helpdesk), the official offline AI Campus Helpdesk Assistant for KLE Technological University (BVB College), Hubballi.",
            "hi": "मैं स्पार्की (कैंपस हेल्पडेस्क) हूँ, केएलई टेक्नोलॉजिकल यूनिवर्सिटी (बीवीबी कॉलेज), हुबली का आधिकारिक ऑफलाइन एआई कैंपस हेल्पडेस्क सहायक।",
            "kn": "ನಾನು ಸ್ಪಾರ್ಕಿ (ಕ್ಯಾಂಪಸ್ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್), ಹುಬ್ಬಳ್ಳಿಯ ಕೆಎಲ್‌ಇ ತಾಂತ್ರಿಕ ವಿಶ್ವವಿದ್ಯಾಲಯದ (ಬಿವಿಬಿ ಕಾಲೇಜು) ಅಧಿಕೃತ ಆಫ್‌ಲೈನ್ AI ಕ್ಯಾಂಪಸ್ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್ ಸಹಾಯಕ.",
        },
        IntentType.CAPABILITIES: {
            "en": "I can help you with campus navigation, department details (ISE, CSE, ECE, Mech, Civil, Biotech, etc.), degree courses (B.E., M.Tech, MBA, MCA, BCA, BBA, Ph.D.), fee structures, hostel timings, campus canteens, vice chancellor info, and admissions at KLE Tech!",
            "hi": "मैं आपको केएलई टेक के विभागों (ISE, CSE, ECE, इत्यादि), पाठ्यक्रमों (B.E., M.Tech, MBA, MCA), शुल्क संरचना, हॉस्टल, कैंटीन, और प्रवेश संबंधी जानकारी दे सकता हूँ!",
            "kn": "ನಾನು ಕೆಎಲ್‌ಇ ಟೆಕ್‌ನ ವಿಭಾಗಗಳು (ISE, CSE, ECE, ಇತ್ಯಾದಿ), ಕೋರ್ಸ್‌ಗಳು (B.E., M.Tech, MBA), ಶುಲ್ಕ ವಿವರ, ಹಾಸ್ಟೆಲ್, ಕ್ಯಾಂಟೀನ್ ಮತ್ತು ಪ್ರವೇಶದ ವಿವರ ನೀಡಬಲ್ಲೆ!",
        },
        IntentType.SMALL_TALK: {
            "en": "I'm doing great and ready to assist you! What campus information are you looking for today?",
            "hi": "मैं बहुत अच्छा हूँ और आपकी सहायता के लिए तैयार हूँ! आज आप परिसर की क्या जानकारी चाहते हैं?",
            "kn": "ನಾನು ಆರಾಮಾಗಿದ್ದೇನೆ ಮತ್ತು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಸಿದ್ಧನಾಗಿದ್ದೇನೆ! ಇಂದು ಕ್ಯಾಂಪಸ್‌ನ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?",
        },
    }

    OUT_OF_DOMAIN_PATTERN = re.compile(
        r"\b(recipe|biryani|fifa|world cup|stock price|tesla|flat tire|camry|quantum|physics|president of france|web scraping|american football|chocolate cake|capital city|photosynthesis|earth to the moon|mona lisa|weather today|movie|song|actor|actress)\b",
        re.IGNORECASE,
    )

    def route(self, message: str, lang_code: str = "en") -> IntentResult:
        """Classify message intent and return pre-formatted response if non-campus intent."""
        clean_text = message.strip()
        return self.classify(clean_text, lang_code=lang_code)

    def classify(self, text: str, lang_code: str = "en") -> IntentResult:
        """Classify user query into IntentType."""
        clean_text = text.strip()
        if not clean_text:
            return IntentResult(IntentType.CAMPUS_QUERY)

        # Check if message contains explicit campus domain keywords
        has_campus_terms = bool(self.CAMPUS_DOMAIN_PATTERN.search(clean_text))
        if has_campus_terms:
            return IntentResult(IntentType.CAMPUS_QUERY)

        # Out of Domain pre-filter for non-campus general queries
        if self.OUT_OF_DOMAIN_PATTERN.search(clean_text):
            return IntentResult(
                IntentType.SMALL_TALK,
                "I couldn't find verified information about that in my knowledge base."
            )

        # Classify conversational intents
        if self.IDENTITY_PATTERN.search(clean_text):
            return IntentResult(IntentType.IDENTITY, self._get_template(IntentType.IDENTITY, lang_code))

        if self.CAPABILITIES_PATTERN.search(clean_text):
            return IntentResult(IntentType.CAPABILITIES, self._get_template(IntentType.CAPABILITIES, lang_code))

        if self.GREETING_PATTERN.search(clean_text):
            return IntentResult(IntentType.GREETING, self._get_template(IntentType.GREETING, lang_code))

        if self.GOODBYE_PATTERN.search(clean_text):
            return IntentResult(IntentType.GOODBYE, self._get_template(IntentType.GOODBYE, lang_code))

        if self.THANKS_PATTERN.search(clean_text):
            return IntentResult(IntentType.THANKS, self._get_template(IntentType.THANKS, lang_code))

        if self.SMALL_TALK_PATTERN.search(clean_text):
            return IntentResult(IntentType.SMALL_TALK, self._get_template(IntentType.SMALL_TALK, lang_code))

        # Default: Campus Query requiring RAG retrieval
        return IntentResult(IntentType.CAMPUS_QUERY)

    def _get_template(self, intent: IntentType, lang_code: str) -> str:
        """Get language-appropriate response template."""
        templates = self.RESPONSE_TEMPLATES.get(intent, {})
        lang = lang_code.lower()
        if lang in templates:
            return templates[lang]
        elif lang in ("kn", "kanglish"):
            return templates.get("kn", templates["en"])
        elif lang in ("hi", "hinglish"):
            return templates.get("hi", templates["en"])
        return templates.get("en", "Hello! How can I help you?")
