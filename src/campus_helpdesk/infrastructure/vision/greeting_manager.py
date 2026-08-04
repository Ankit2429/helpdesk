"""
src/campus_helpdesk/infrastructure/vision/greeting_manager.py

Time-Aware and Random Greeting Generator with Cooldown Debouncing for AUNTII Helpdesk Robot.
"""

from __future__ import annotations

import datetime
import logging
import random
import time

logger = logging.getLogger("campus_helpdesk.greeting_manager")


class GreetingManager:
    """
    Manages time-aware & random greetings with strict cooldown debouncing (5-10 seconds)
    to prevent repeated triggers.
    """

    def __init__(self, cooldown_seconds: float = 7.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.last_greeting_time: float = 0.0
        self.last_greeted_user_id: int | None = None

        self.multilingual_greetings = {
            "en": {
                "morning": "Good Morning!",
                "afternoon": "Good Afternoon!",
                "evening": "Good Evening!",
                "hello": "Hello!",
                "pool": [
                    "Welcome to KLE Technological University. How may I help you today?",
                    "Hi there! Ask me anything about courses, admissions, or hostels.",
                    "Good to see you! Sparky is ready to assist you.",
                ],
            },
            "kn": {
                "morning": "ಶುಭೋದಯ!",
                "afternoon": "ಶುಭಾಹ್ನ!",
                "evening": "ಶುಭ ಸಂಜೆ!",
                "hello": "ನಮಸ್ಕಾರ!",
                "pool": [
                    "ಕೆಎಲ್‌ಇ ತಾಂತ್ರಿಕ ವಿಶ್ವವಿದ್ಯಾಲಯಕ್ಕೆ ಸುಸ್ವಾಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
                    "ನಮಸ್ಕಾರ! ಕೋರ್ಸ್‌ಗಳು, ಪ್ರವೇಶಾತಿ ಅಥವಾ ಹಾಸ್ಟೆಲ್‌ಗಳ ಬಗ್ಗೆ ಏನನ್ನಾದರೂ ಕೇಳಿ.",
                    "ನಿಮ್ಮನ್ನು ನೋಡಿ ಸಂತೋಷವಾಯಿತು! ಸ್ಪಾರ್ಕಿ ನಿಮ್ಮ ಸಹಾಯಕ್ಕೆ ಸಿದ್ಧವಾಗಿದೆ.",
                ],
            },
            "hi": {
                "morning": "शुभ प्रभात!",
                "afternoon": "शुभ दोपहर!",
                "evening": "शुभ संध्या!",
                "hello": "नमस्ते!",
                "pool": [
                    "केएलई टेक्नोलॉजिकल यूनिवर्सिटी में आपका स्वागत है। मैं आपकी क्या सहायता कर सकता हूँ?",
                    "नमस्ते! पाठ्यक्रमों, प्रवेश या हॉस्टल के बारे में कुछ भी पूछें।",
                    "आपको देखकर अच्छा लगा! स्पार्की आपकी सहायता के लिए तैयार है।",
                ],
            },
        }

    def is_cooldown_active(self, user_id: int | None = None) -> bool:
        """Check if greeting cooldown is active."""
        now = time.time()
        elapsed = now - self.last_greeting_time
        if elapsed < self.cooldown_seconds:
            return True
        return False

    def generate_greeting(self, user_name: str | None = None, user_id: int | None = None, language: str = "en") -> str:
        """
        Generate time-aware or random greeting string in the active conversation language.
        """
        lang = language.lower() if language else "en"
        if lang not in self.multilingual_greetings:
            lang = "en"

        g_dict = self.multilingual_greetings[lang]
        now_dt = datetime.datetime.now()
        hour = now_dt.hour

        if 5 <= hour < 12:
            time_prefix = g_dict["morning"]
        elif 12 <= hour < 17:
            time_prefix = g_dict["afternoon"]
        elif 17 <= hour < 22:
            time_prefix = g_dict["evening"]
        else:
            time_prefix = g_dict["hello"]

        random_choice = random.choice(g_dict["pool"])

        if user_name:
            greeting_str = f"{time_prefix} {user_name}, {random_choice}"
        else:
            greeting_str = f"{time_prefix} {random_choice}"

        self.last_greeting_time = time.time()
        self.last_greeted_user_id = user_id
        logger.info(f"[Greeting Generated] Language='{lang}': '{greeting_str}' (User ID #{user_id})")

        return greeting_str

    def reset_cooldown(self) -> None:
        """Reset cooldown timestamp manually."""
        self.last_greeting_time = 0.0
        self.last_greeted_user_id = None
