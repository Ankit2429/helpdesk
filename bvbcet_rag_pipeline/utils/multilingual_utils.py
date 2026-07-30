"""Multilingual Processing & Script Normalization Utilities.

Provides query language detection, Unicode NFKD text normalization,
diacritic stripping, non-Latin script processing (e.g. Kannada, Hindi),
and embedding model routing based on detected query language.
"""

import re
import unicodedata
from typing import Dict, Tuple

from logger.logger import get_logger

logger = get_logger("multilingual_utils")

# Script regex ranges
KANNADA_RANGE = re.compile(r"[\u0C80-\u0CFF]")
DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")
LATIN_RANGE = re.compile(r"[a-zA-Z]")


def detect_language(text: str) -> Tuple[str, float]:
    """Detect text language using script analysis and character distribution.

    Returns:
        Tuple of (language_code, confidence_score)
        Language codes: 'en' (English), 'kn' (Kannada), 'hi' (Hindi/Devanagari), 'multilingual'.
    """
    if not text or not text.strip():
        return "en", 1.0

    kannada_chars = len(KANNADA_RANGE.findall(text))
    devanagari_chars = len(DEVANAGARI_RANGE.findall(text))
    latin_chars = len(LATIN_RANGE.findall(text))
    total_chars = max(1, len(text))

    if kannada_chars > 0 and kannada_chars >= devanagari_chars:
        confidence = min(1.0, round(kannada_chars / total_chars * 3.0, 2))
        return "kn", max(0.60, confidence)
    elif devanagari_chars > 0:
        confidence = min(1.0, round(devanagari_chars / total_chars * 3.0, 2))
        return "hi", max(0.60, confidence)
    elif latin_chars > 0:
        return "en", 0.95
    else:
        return "en", 0.50


def normalize_text(text: str, remove_diacritics: bool = True) -> str:
    """Normalize text using Unicode NFKD normalization and diacritic stripping."""
    if not text:
        return ""

    # Unicode NFKD decomposition
    normalized = unicodedata.normalize("NFKD", text)

    if remove_diacritics:
        # Strip combining diacritical marks
        normalized = "".join(
            c for c in normalized if unicodedata.category(c) != "Mn"
        )

    # Clean whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def select_model_for_language(
    lang_code: str,
    default_model: str = "all-MiniLM-L6-v2",
    multilingual_model: str = "intfloat/multilingual-e5-base",
) -> str:
    """Select appropriate embedding model based on language code."""
    if lang_code in ["kn", "hi", "multilingual"]:
        logger.info(f"Detected non-English script '{lang_code}'. Routing to multilingual model '{multilingual_model}'")
        return multilingual_model
    return default_model
