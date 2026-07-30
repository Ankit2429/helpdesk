"""Transliteration, Hinglish/Kanglish Script Processing & Proper Noun Protection.

Provides per-turn language detection including Romanized transliterations
(Hinglish, Kanglish), handles code-switching, and preserves non-translatable proper nouns.
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Set, Tuple

from logger.logger import get_logger
from utils.multilingual_utils import detect_language

logger = get_logger("transliteration_utils")

# Preserved technical & campus proper nouns
PROTECTED_PROPER_NOUNS: Set[str] = {
    "KLE Tech",
    "BVBCET",
    "KCET",
    "COMEDK",
    "B.E.",
    "M.Tech",
    "MBA",
    "MCA",
    "Ph.D",
    "Computer Science",
    "Civil Engineering",
    "Mechanical Engineering",
    "B-Block",
    "Central Library",
    "Hubballi",
}

# Key transliteration vocabulary patterns
HINGLISH_KEYWORDS = re.compile(
    r"\b(kitna|kitni|kaise|kab|kahan|kyun|fees|hota|hai|hote|hain|batao|chahiye|milega|sath|aur)\b",
    re.IGNORECASE,
)
KANGLISH_KEYWORDS = re.compile(
    r"\b(eppaga|yavaga|yelli|hege|beku|aguthe|sikkathe|yaava|nalli|kodi|helu|kannada|ide)\b",
    re.IGNORECASE,
)


@dataclass
class LanguageAnalysisResult:
    """Dataclass holding turn language detection and code-switching analysis."""

    primary_language: str  # 'en', 'kn', 'hi', 'hinglish', 'kanglish', 'code_switched'
    is_transliterated: bool
    is_code_switched: bool
    detected_scripts: List[str]
    protected_nouns_found: List[str]


class TransliterationProcessor:
    """Per-turn language detection and transliteration processor."""

    @staticmethod
    def analyze_turn_language(query: str) -> LanguageAnalysisResult:
        """Analyze query string for language, transliteration (Hinglish/Kanglish), and code-switching."""
        if not query or not query.strip():
            return LanguageAnalysisResult(
                primary_language="en",
                is_transliterated=False,
                is_code_switched=False,
                detected_scripts=["Latin"],
                protected_nouns_found=[],
            )

        # Step 1: Detect protected proper nouns
        found_nouns = [
            noun for noun in PROTECTED_PROPER_NOUNS
            if (re.search(r"\b" + re.escape(noun) + r"\b", query, re.I) or noun.lower() in query.lower())
        ]

        # Step 2: Native script detection via multilingual_utils
        native_lang, conf = detect_language(query)

        detected_scripts = []
        if native_lang == "kn":
            detected_scripts.append("Kannada")
        elif native_lang == "hi":
            detected_scripts.append("Devanagari")
        else:
            detected_scripts.append("Latin")

        # Step 3: Check for Romanized Transliteration (Hinglish / Kanglish)
        hinglish_hits = len(HINGLISH_KEYWORDS.findall(query))
        kanglish_hits = len(KANGLISH_KEYWORDS.findall(query))

        is_transliterated = False
        is_code_switched = False
        primary_lang = native_lang

        if native_lang == "en":
            if kanglish_hits >= 1:
                primary_lang = "kanglish"
                is_transliterated = True
            elif hinglish_hits >= 1:
                primary_lang = "hinglish"
                is_transliterated = True

        if len(detected_scripts) > 1 or (is_transliterated and found_nouns):
            is_code_switched = True

        logger.info(f"Analyzed turn query: '{query}' -> Primary Lang: '{primary_lang}' (Transliterated={is_transliterated})")
        return LanguageAnalysisResult(
            primary_language=primary_lang,
            is_transliterated=is_transliterated,
            is_code_switched=is_code_switched,
            detected_scripts=detected_scripts,
            protected_nouns_found=found_nouns,
        )

    @staticmethod
    def preserve_proper_nouns(text: str, protected_nouns: List[str]) -> str:
        """Ensure proper nouns remain untranslated and properly formatted in output text."""
        result = text
        for noun in protected_nouns:
            pattern = re.compile(r"\b" + re.escape(noun) + r"\b", re.I)
            result = pattern.sub(noun, result)
        return result
