"""
ttt_service.py
Text-to-Text (TTT) intent understanding & response generation service.

Extensible rule-based intent matching service designed for offline operation.
Supports simple intent patterns (greeting, time, weather, capabilities) and
can easily be extended with additional rules or domain RAG backends.
"""

import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ttt_service")


class TTTService:
    """Text-to-Text understanding and reply generation service."""

    def __init__(self):
        self._init_intents()

    def _init_intents(self) -> None:
        """Initialize rule-based intent patterns and response generators."""
        self._intent_rules = [
            (
                r"(hello|hi|hey|greetings|namaste|namaskara|नमस्ते|ನಮಸ್ಕಾರ)",
                self._handle_greeting,
            ),
            (
                r"(time|clock|समय|ಸಮಯ)",
                self._handle_time,
            ),
            (
                r"(weather|temperature|forecast|rain|sunny|hot|cold|मौसम|ಹವಾಮಾನ)",
                self._handle_weather,
            ),
            (
                r"(what can you do|help|capabilities|who are you|function|features|सहायता|ಸಹಾಯ)",
                self._handle_capabilities,
            ),
        ]

    def _handle_greeting(self, text: str, language: str) -> str:
        if language in ("hi", "hin"):
            return "नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ?"
        elif language in ("kn", "kan"):
            return "ನಮಸ್ಕಾರ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        return "Hello! Welcome to our campus. How can I assist you today?"

    def _handle_time(self, text: str, language: str) -> str:
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        if language in ("hi", "hin"):
            return f"अभी समय {now_str} है।"
        elif language in ("kn", "kan"):
            return f"ಈಗ ಸಮಯ {now_str} ಆಗಿದೆ."
        return f"It is currently {now_str}."

    def _handle_weather(self, text: str, language: str) -> str:
        if language in ("hi", "hin"):
            return "आज परिसर का मौसम सुहावना और साफ़ है।"
        elif language in ("kn", "kan"):
            return "ಇಂದು ಕ್ಯಾಂಪಸ್‌ನಲ್ಲಿ ಹವಾಮಾನ ಚೆನ್ನಾಗಿದೆ."
        return "The campus weather is currently pleasant with clear skies."

    def _handle_capabilities(self, text: str, language: str) -> str:
        if language in ("hi", "hin"):
            return "मैं परिसर की दिशाओं, पुस्तकालय के समय, और विभाग की जानकारी में सहायता कर सकता हूँ।"
        elif language in ("kn", "kan"):
            return "ನಾನು ಕ್ಯಾಂಪಸ್ ದಾರಿಗಳು, ಲೈಬ್ರರಿ ಸಮಯ ಮತ್ತು ವಿಭಾಗದ ಮಾಹಿತಿಯಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಹುದು."
        return (
            "I am your Campus Helpdesk Robot! I can help you with campus directions, "
            "library hours, department locations, and general student guidance."
        )

    def get_reply(self, user_text: str, language: str = "en") -> str:
        """
        Generate a text response for `user_text` in specified `language`.

        Args:
            user_text: Transcribed input string from user.
            language: Language code ("en", "hi", "kn", etc.).

        Returns:
            str: Generated reply string.
        """
        if not user_text or not user_text.strip():
            return "I didn't catch that. Please speak clearly into the microphone."

        cleaned_text = user_text.lower().strip()
        logger.info(f"Processing input ('{language}'): \"{user_text}\"")

        for pattern, handler in self._intent_rules:
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                reply = handler(cleaned_text, language)
                logger.info(f"Matched intent rule -> \"{reply}\"")
                return reply

        # Fallback response if no intent rule matches
        fallback_reply = (
            f"You asked: \"{user_text}\". "
            "For specific campus queries, please ask about library hours, campus locations, or time."
        )
        logger.info(f"Fallback response -> \"{fallback_reply}\"")
        return fallback_reply


# ---- Quick manual test -------------------------------------------------------
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ttt = TTTService()

    test_inputs = [
        ("Hello there!", "en"),
        ("What time is it?", "en"),
        ("How is the weather today?", "en"),
        ("What can you do?", "en"),
        ("Where is the computer science building?", "en"),
        ("नमस्ते", "hi"),
        ("ನಮಸ್ಕಾರ", "kn"),
    ]

    print("\n--- TTT Service Intent Tests ---")
    for text, lang in test_inputs:
        reply = ttt.get_reply(text, language=lang)
        print(f"\nUser [{lang.upper()}]: {text}")
        print(f"Robot:       {reply}")
