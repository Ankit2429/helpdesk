"""Modular Intent Classifier Engine.

Detects conversational intents (Greeting, Thanks, Goodbye, SmallTalk, Question, Unknown)
and provides quick response generators for non-information queries.
"""

from enum import Enum
import re
from typing import Optional
from logger.logger import get_logger

logger = get_logger("intent_classifier")


class Intent(str, Enum):
    """Supported conversational intent types."""

    GREETING = "Greeting"
    THANKS = "Thanks"
    GOODBYE = "Goodbye"
    SMALL_TALK = "SmallTalk"
    QUESTION = "Question"
    UNKNOWN = "Unknown"


class IntentClassifier:
    """Classifies user inputs into Intent types and provides direct responses."""

    GREETING_PATTERNS = [
        r"^\s*(hi|hello|hey|greetings|good\s*(morning|afternoon|evening)|namaste|yo|hey\s*there)\s*[\!\.\?]*\s*$",
        r"\b(hi|hello|hey|greetings|good\s*(morning|afternoon|evening)|namaste)\b",
    ]

    THANKS_PATTERNS = [
        r"^\s*(thank\s*you|thanks|thanking|thankful|much\s*appreciated|thx|ty)\s*[\!\.\?]*\s*$",
        r"\b(thank\s*you|thanks|much\s*appreciated)\b",
    ]

    GOODBYE_PATTERNS = [
        r"^\s*(bye|goodbye|see\s*you|take\s*care|exit|quit|cya)\s*[\!\.\?]*\s*$",
        r"\b(bye|goodbye|see\s*you|take\s*care)\b",
    ]

    SMALL_TALK_PATTERNS = [
        r"\b(how\s*are\s*you|who\s*are\s*you|what\s*is\s*your\s*name|are\s*you\s*a\s*bot|what\s*can\s*you\s*do|ok|okay|yes|yeah|sure|got\s*it|cool|fine|alright)\b",
    ]

    CANNED_RESPONSES = {
        Intent.GREETING: "Hello! Welcome to KLE Technological University AI Campus Helpdesk. How can I help you today?",
        Intent.THANKS: "You're very welcome! Feel free to ask if you have any more questions about KLE Tech.",
        Intent.GOODBYE: "Goodbye! Have a great day ahead at KLE Technological University.",
        Intent.SMALL_TALK: "I am Sparky, the official AI Campus Assistant for KLE Tech. I can help answer questions about courses, admissions, fees, departments, and campus facilities.",
    }

    def classify(self, text: str) -> Intent:
        """Classify input string into an Intent enum."""
        if not text or not text.strip():
            return Intent.UNKNOWN

        clean_text = text.strip().lower()

        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, clean_text):
                logger.info(f"Intent detected: GREETING for query '{text[:30]}'")
                return Intent.GREETING

        for pattern in self.THANKS_PATTERNS:
            if re.search(pattern, clean_text):
                logger.info(f"Intent detected: THANKS for query '{text[:30]}'")
                return Intent.THANKS

        for pattern in self.GOODBYE_PATTERNS:
            if re.search(pattern, clean_text):
                logger.info(f"Intent detected: GOODBYE for query '{text[:30]}'")
                return Intent.GOODBYE

        for pattern in self.SMALL_TALK_PATTERNS:
            if re.search(pattern, clean_text):
                logger.info(f"Intent detected: SMALL_TALK for query '{text[:30]}'")
                return Intent.SMALL_TALK

        logger.info(f"Intent detected: QUESTION for query '{text[:30]}'")
        return Intent.QUESTION

    def get_canned_response(self, intent: Intent) -> Optional[str]:
        """Return direct response for non-question intents."""
        return self.CANNED_RESPONSES.get(intent)
