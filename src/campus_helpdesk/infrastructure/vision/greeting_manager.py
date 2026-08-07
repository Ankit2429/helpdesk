"""
src/campus_helpdesk/infrastructure/vision/greeting_manager.py

Time-Aware and Random Greeting Generator with Cooldown Debouncing for AUNTII Helpdesk Robot.

v1.1 — Added per-session guard: when ``per_session_guard=True`` (default),
a greeting is blocked for the lifetime of the current presence session,
regardless of the cooldown timer or tracker-ID recycling.  Call
``reset_session()`` (or ``reset_cooldown()``) to allow a new greeting after
the person has left.
"""

from __future__ import annotations

import datetime
import logging
import random
import time

logger = logging.getLogger("campus_helpdesk.greeting_manager")


class GreetingManager:
    """
    Manages time-aware & random greetings with strict cooldown debouncing and
    an optional per-session guard to prevent repeated greetings while the same
    person remains in view.

    Parameters
    ----------
    cooldown_seconds:
        Minimum time (seconds) between any two greetings.  Default: 7.0.
    per_session_guard:
        If True, a greeting is blocked once fired for the current session,
        independent of the cooldown timer.  Reset with ``reset_session()``
        or ``reset_cooldown()``.  Default: True.
    """

    def __init__(
        self,
        cooldown_seconds: float = 7.0,
        per_session_guard: bool = True,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.per_session_guard = per_session_guard

        self.last_greeting_time: float = 0.0
        self.last_greeted_user_id: int | None = None

        # Per-session guard flag — set True on first greeting, cleared by reset_session()
        self._session_greeted: bool = False

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
        """Check if greeting is blocked by cooldown timer or per-session guard."""
        # Per-session guard takes priority: if we already greeted this session, block.
        if self.per_session_guard and self._session_greeted:
            return True
        # Fallback: time-based cooldown
        now = time.time()
        elapsed = now - self.last_greeting_time
        if elapsed < self.cooldown_seconds:
            return True
        return False

    def generate_greeting(
        self,
        user_name: str | None = None,
        user_id: int | None = None,
        language: str = "en",
    ) -> str:
        """
        Generate time-aware or random greeting string in the active conversation language.
        Records the greeting time and sets the per-session guard.
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
        self._session_greeted = True  # Lock greeting for this session

        logger.info(
            "[Greeting Generated] Language='%s': '%s' (User ID #%s)",
            lang,
            greeting_str,
            user_id,
        )

        return greeting_str

    def reset_session(self) -> None:
        """Reset the per-session guard to allow a new greeting on next visit.

        Call this when the person has definitively left (PERSON_LEFT fires).
        Does not reset the cooldown timer — back-to-back visits still respect
        the time-based cooldown.
        """
        self._session_greeted = False
        self.last_greeted_user_id = None
        logger.debug("[GreetingManager] Session reset — next visitor may be greeted.")

    def reset_cooldown(self) -> None:
        """Reset both cooldown timestamp and session guard manually (e.g., for tests)."""
        self.last_greeting_time = 0.0
        self.last_greeted_user_id = None
        self._session_greeted = False
